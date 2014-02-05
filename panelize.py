#!/usr/bin/python

from lxml import etree
import argparse
import sys

LAYER_DIMENSION = '20'
LAYER_VSCORE = '102'

VSCORE_OUT_LENGTH = 5.0 # mm
DRILL_DEFAULT = 3.2 # mm

# Copy src as child of dst.
def shallowCopy(dst, src):
  elem = etree.SubElement(dst, src.tag)

  # Copy text inside open/close tags.
  elem.text = src.text

  # Copy attributes
  for k, v in src.items():
    elem.set(k, v)
  return elem

class Panelizer:
  def __init__(self, cols, rows, colspacing, rowspacing, hframe, vframe, holex, holey, drill, **kw):
    # Number of columns and rows.
    self.cols = cols
    self.rows = rows

    # Board gap width.
    self.colspacing = colspacing # mm
    self.rowspacing = rowspacing # mm

    # Frame width
    self.hframe = hframe # mm or zero
    self.vframe = vframe # mm or zero

    # Holes
    self.holex = holex # mm
    self.holey = holey # mm
    self.drill = drill # mm

    # Offset distance to the next board.
    self.coloffset = 0.0 # mm
    self.rowoffset = 0.0 # mm

    # Board dimension.
    self.minx = 0.0 # mm
    self.maxx = 0.0 # mm
    self.miny = 0.0 # mm
    self.maxy = 0.0 # mm
    self.dimensionwidth = 0.0 # mm

    # Panel dimension.
    self.panelminx = 0.0 # mm
    self.panelmaxx = 0.0 # mm
    self.panelminy = 0.0 # mm
    self.panelmaxy = 0.0 # mm

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
    xs = dict()
    ys = dict()
    for elem in plain:
      if elem.tag == 'wire' and elem.get('layer') == LAYER_VSCORE:
        # Process Vscore lines.
        w = float(elem.get('width'))

        # Check if vertical
        x1 = elem.get('x1')
        x2 = elem.get('x2')
        if x1 == x2:
          x = float(x1)
          for i in range(self.cols):
            xs[x] = max(xs.get(x, 0.0), w)
            x += self.coloffset

        # Check if horizontal
        y1 = elem.get('y1')
        y2 = elem.get('y2')
        if y1 == y2:
          y = float(y1)
          for i in range(self.rows):
            ys[y] = max(ys.get(y, 0.0), w)
            y += self.rowoffset
        # Add the elements later.

      else:
        # Process other elements.
        for x in range(self.cols):
          for y in range(self.rows):
            self.offsetCopy(dstplain, elem, x, y, False)

    # Function to add wire
    def wire(x1, x2, y1, y2, width, layer):
      elem = etree.SubElement(dstplain, 'wire')
      elem.set('x1', x1)
      elem.set('x2', x2)
      elem.set('y1', y1)
      elem.set('y2', y2)
      elem.set('width', width)
      elem.set('layer', layer)

    # Add vertical Vscore wires.
    y1 = str(self.panelminy - VSCORE_OUT_LENGTH)
    y2 = str(self.panelmaxy + VSCORE_OUT_LENGTH)
    for x, w in xs.items():
      x = str(x)
      wire(x, x, y1, y2, str(w), LAYER_VSCORE)

    # Add vertical Vscore wires.
    x1 = str(self.panelminx - VSCORE_OUT_LENGTH)
    x2 = str(self.panelmaxx + VSCORE_OUT_LENGTH)
    for y, w in ys.items():
      y = str(y)
      wire(x1, x2, y, y, str(w), LAYER_VSCORE)

    # Add dimension
    x1 = str(self.panelminx)
    x2 = str(self.panelmaxx)
    y1 = str(self.panelminy)
    y2 = str(self.panelmaxy)
    w = str(self.dimensionwidth)
    wire(x1, x1, y1, y2, w, LAYER_DIMENSION)
    wire(x2, x2, y1, y2, w, LAYER_DIMENSION)
    wire(x1, x2, y1, y1, w, LAYER_DIMENSION)
    wire(x1, x2, y2, y2, w, LAYER_DIMENSION)

    # Function to add wire
    def hole(x, y, drill):
      elem = etree.SubElement(dstplain, 'hole')
      elem.set('x', x)
      elem.set('y', y)
      elem.set('drill', drill)

    # Add holes
    if self.holex > 0.0 and self.holey > 0.0 and self.drill > 0.0:
      x1 = str(self.panelminx + self.holex)
      x2 = str(self.panelmaxx - self.holex)
      y1 = str(self.panelminy + self.holey)
      y2 = str(self.panelmaxy - self.holey)
      d = str(self.drill)
      hole(x1, y1, d)
      hole(x1, y2, d)
      hole(x2, y1, d)
      hole(x2, y2, d)

  def panelizeXML(self, src):
    eagle = src.getroot()
    if eagle.tag != 'eagle':
      raise 'XML %s not supported.' % eagle.tag

    # Find board dimension.
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
        self.dimensionwidth = max(self.dimensionwidth, float(elem.get('width')))
    if len(xs) == 0 or len(ys) == 0:
      raise 'No dimension found.'
    self.minx = min(xs)
    self.maxx = max(xs)
    self.miny = min(ys)
    self.maxy = max(ys)
    self.coloffset = (self.maxx - self.minx) + self.colspacing
    self.rowoffset = (self.maxy - self.miny) + self.rowspacing

    # Panel dimension
    self.panelminx = self.minx - self.vframe
    self.panelmaxx = self.minx + self.coloffset * self.cols - self.colspacing + self.vframe
    self.panelminy = self.miny - self.hframe
    self.panelmaxy = self.miny + self.rowoffset * self.rows - self.rowspacing + self.hframe

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
  argparser.add_argument('--colspacing', type=float, default=0.0,
      help='Column spacing width in mm (float).')
  argparser.add_argument('--rowspacing', type=float, default=0.0,
      help='Row spacing height in mm (float).')
  argparser.add_argument('--hframe', type=float, default=0.0,
      help='Horizontal frame height in mm (float).')
  argparser.add_argument('--vframe', type=float, default=0.0,
      help='Vertical frame height in mm (float).')
  argparser.add_argument('--holex', type=float, default=0.0,
      help='Hole X position offset from edge in mm (float).')
  argparser.add_argument('--holey', type=float, default=0.0,
      help='Hole Y position offset from edge in mm (float).')
  argparser.add_argument('--drill', type=float, default=DRILL_DEFAULT,
      help='Hole drill size in mm (float).')
  argparser.add_argument('--stdout', action='store_true', default=False,
      help='Write to stdout instead of file.')
  argparser.add_argument('file', type=str, nargs='+',
      help='EAGLE CAD brd file to process.')

  args = argparser.parse_args()

  if args.cols < 1 or args.rows < 1:
    print 'cols and rows must be 1 or more.'
    sys.exit(1)
  if args.colspacing < 0.0 or args.rowspacing < 0.0:
    print 'colspacing and colspacing must not be negative.'
    sys.exit(1)
  if args.hframe < 0.0 or args.vframe < 0.0:
    print 'hframe and vframe must not be negative.'
    sys.exit(1)
  if args.holex < 0.0 or args.holey < 0.0:
    print 'holex and holey must not be negative.'
    sys.exit(1)
  if args.drill <= 0.0:
    print 'drill must be positive.'
    sys.exit(1)

  panelizer = Panelizer(**vars(args))

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
