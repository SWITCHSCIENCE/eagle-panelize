#!/usr/bin/python

from lxml import etree
import argparse
import sys

LAYER_DIMENSION = '20'
LAYER_VSCORE = '102'

# Copy src as child of dst.
def shallowCopy(dst, src):
  elem = etree.SubElement(dst, src.tag)
  elem.text = src.text
  for k, v in src.items():
    elem.set(k, v)
  return elem

class Panelizer:
  def __init__(self, cols, rows, colspacing, rowspacing, hframe, vframe):
    self.cols = cols
    self.rows = rows
    self.colspacing = colspacing # mm
    self.rowspacing = rowspacing # mm
    self.hframe = hframe # mm or zero
    self.vframe = vframe # mm or zero
    self.coloffset = 0.0 # mm
    self.rowoffset = 0.0 # mm

  # Copy src as child of dst.
  def offsetCopy(self, dst, src, x, y, recursive):
    elem = etree.SubElement(dst, src.tag)
    elem.text = src.text
    for k, v in src.items():
      if k == 'name':
        elem.set(k, '%s-%d-%d' % (v, x, y))
      elif k == 'element':
        elem.set(k, '%s-%d-%d' % (v, x, y))
      elif k in ['x', 'x1', 'x2']:
        elem.set(k, str(float(v) + x * self.coloffset))
      elif k in ['y', 'y1', 'y2']:
        elem.set(k, str(float(v) + y * self.rowoffset))
      else:
        elem.set(k, v)
    if recursive:
      for child in src:
        self.offsetCopy(elem, child, x, y, True)
    return elem

  def copyPlain(self, dstplain, plain):
    for elem in plain:
      if elem.tag == 'wire' and elem.get('layer') == LAYER_VSCORE:
        # Process Vscore lines.
        x1 = elem.get('x1')
        x2 = elem.get('x2')
        y1 = elem.get('y1')
        y2 = elem.get('y2')
        if x1 == x2:
          # Vertical
          y1f = float(y1)
          y2f = float(y2)
          if y1f > y2f:
            y1 = str(y1f + self.rows * self.rowoffset - self.rowoffset)
          else:
            y2 = str(y2f + self.rows * self.rowoffset - self.rowoffset)
          for x in range(self.cols):
            x = str(float(x1) + x * self.coloffset)
            e = shallowCopy(dstplain, elem)
            e.set('x1', x)
            e.set('x2', x)
            e.set('y1', y1)
            e.set('y2', y2)
        elif y1 == y2:
          # Horizontal
          x1f = float(x1)
          x2f = float(x2)
          if x1f > x2f:
            x1 = str(x1f + self.cols * self.coloffset - self.coloffset)
          else:
            x2 = str(x2f + self.cols * self.coloffset - self.coloffset)
          for y in range(self.rows):
            y = str(float(y1) + y * self.rowoffset)
            e = shallowCopy(dstplain, elem)
            e.set('x1', x1)
            e.set('x2', x2)
            e.set('y1', y)
            e.set('y2', y)
      else:
        # Process other elements.
        for x in range(self.cols):
          for y in range(self.rows):
            self.offsetCopy(dstplain, elem, x, y, False)

  def panelizeXML(self, src):
    eagle = src.getroot()
    if eagle.tag != 'eagle':
      raise 'XML %s not supported.' % eagle.tag

    # Find dimension.
    xs = []
    ys = []
    plain = src.xpath('/eagle/drawing/board/plain')
    if not plain:
      raise 'No <plain> found.'
    plain = plain[0]
    for elem in plain:
      #XXX Arc and circle not yet supported.
      if elem.tag == 'wire' and elem.get('layer') == LAYER_DIMENSION:
        xs.append(float(elem.get('x1')))
        xs.append(float(elem.get('x2')))
        ys.append(float(elem.get('y1')))
        ys.append(float(elem.get('y2')))
    if len(xs) == 0 or len(ys) == 0:
      raise 'No dimension found.'
    self.minx = min(xs)
    self.maxx = max(xs)
    self.miny = min(ys)
    self.maxy = max(ys)
    self.coloffset = (self.maxx - self.minx) + self.colspacing
    self.rowoffset = (self.maxy - self.miny) + self.rowspacing

    # Copy root element <eagle>.
    dsteagle = etree.Element('eagle')
    for k, v in eagle.items():
      dsteagle.set(k, v) # copy attributes.
    dst = etree.ElementTree(dsteagle)

    # Variable to save part names.
    partnames = etree.Element('partnames')

    # Process whole tree.
    for child in eagle:
      if child.tag == 'drawing':
        drawing = child
        dstdrawing = shallowCopy(dsteagle, child)
        for child in drawing:
          if child.tag == 'board':
            board = child
            dstboard = shallowCopy(dstdrawing, child)
            for child in board:
              if child.tag == 'plain':
                dstplain = shallowCopy(dstboard, child)
                self.copyPlain(dstplain, child)

              elif child.tag == 'elements':
                # Process parts.
                elements = child
                dstelements = shallowCopy(dstboard, child)
                for x in range(self.cols):
                  for y in range(self.rows):
                    for element in elements:
                      self.offsetCopy(dstelements, element, x, y, False)

                      # Save part name texts for later addition to <plain>
                      attribute = element.find('attribute')
                      if attribute != None:
                        partname = etree.SubElement(partnames, 'text')
                        partname.text = element.get('name')
                        for k, v in attribute.items():
                          if k == 'x':
                            partname.set(k, str(float(v) + x * self.coloffset))
                          elif k == 'y':
                            partname.set(k, str(float(v) + y * self.rowoffset))
                          elif k != 'name':
                            partname.set(k, v)

              elif child.tag == 'signals':
                # Process copper.
                signals = child
                dstsignals = shallowCopy(dstboard, child)
                for x in range(self.cols):
                  for y in range(self.rows):
                    for signal in signals:
                      self.offsetCopy(dstsignals, signal, x, y, True)

              else:
                dstboard.append(child)
          else:
            dstdrawing.append(child)
      else:
        dsteagle.append(child)

    # Copy part name texts.
    if dstplain != None:
      for elem in partnames:
        dstplain.append(elem)

    return dst

  def panelizeFile(self, infile, out):
    # infile: file name or file object
    # out: file object
    xmlparser = etree.XMLParser(remove_blank_text=True)
    out.write(
      etree.tostring(
        self.panelizeXML(etree.parse(infile, xmlparser)),
        encoding='UTF-8', xml_declaration=True,
        pretty_print=True
      )
    )

def main():
  argparser = argparse.ArgumentParser(
      description='Panelizer for EAGLE CAD brd file.')
  argparser.add_argument('--cols', type=int, required=True,
      help='Number of colmns (integer).')
  argparser.add_argument('--rows', type=int, required=True,
      help='Number of rows (integer).')
  argparser.add_argument('--colspacing', type=float,
      help='Column spacing width in mm (float).')
  argparser.add_argument('--rowspacing', type=float,
      help='Row spacing height in mm (float).')
  argparser.add_argument('--stdout', action='store_true', default=False,
      help='Write to stdout instead of file.')
  argparser.add_argument('file', type=str, nargs='+',
      help='EAGLE CAD brd file to process.')

  args = argparser.parse_args()

  if args.cols < 1 or args.rows < 1:
    print 'cols or rows not properly set.'
    sys.exit(1)
  if args.colspacing < 0.0 or args.colspacing < 0.0:
    print 'colspacing or colspacing not properly set.'
    sys.exit(1)

  panelizer = Panelizer(
    cols=args.cols, rows=args.rows,
    colspacing=args.colspacing, rowspacing=args.rowspacing,
    hframe=0.0, vframe=0.0,
  )

  for fname in args.file:
    if fname == '-':
      infile = sys.stdin
      args.stdout = True
    else:
      infile = fname

    if args.stdout:
      out = sys.stdout
    else:
      a = fname.rsplit('.', 1) + ['']
      out = open('%s-panel.%s' % (a[0], a[1]), 'w+') # raise

    panelizer.panelizeFile(infile, out)

if __name__ == '__main__':
  main()
