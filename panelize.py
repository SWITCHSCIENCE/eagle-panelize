#!/usr/bin/python

from lxml import etree
import argparse
import sys

cols = 0
rows = 0
coloffset = 0.0 # mm
rowoffset = 0.0 # mm

LAYER_VSCORE = '102'

# Copy src as child of dst.
def shallowCopy(dst, src):
  elem = etree.SubElement(dst, src.tag)
  elem.text = src.text
  for k, v in src.items():
    elem.set(k, v)
  return elem

# Copy src as child of dst.
def offsetCopy(dst, src, x, y, recursive):
  elem = etree.SubElement(dst, src.tag)
  elem.text = src.text
  for k, v in src.items():
    if k == 'name':
      elem.set(k, '%s-%d-%d' % (v, x, y))
    elif k == 'element':
      elem.set(k, '%s-%d-%d' % (v, x, y))
    elif k in ['x', 'x1', 'x2']:
      elem.set(k, str(float(v) + x * coloffset))
    elif k in ['y', 'y1', 'y2']:
      elem.set(k, str(float(v) + y * rowoffset))
    else:
      elem.set(k, v)
  if recursive:
    for child in src:
      offsetCopy(elem, child, x, y, True)
  return elem

def copyPlain(dstplain, plain):
  for elem in plain:
    if elem.tag == 'wire' and elem.get('layer') == LAYER_VSCORE:
      x1 = elem.get('x1')
      x2 = elem.get('x2')
      y1 = elem.get('y1')
      y2 = elem.get('y2')
      if x1 == x2:
        # Vertical
        y1f = float(y1)
        y2f = float(y2)
        if y1f > y2f:
          y1 = str(y1f + rows * rowoffset - rowoffset)
        else:
          y2 = str(y2f + rows * rowoffset - rowoffset)
        for x in range(cols):
          x = str(float(x1) + x * coloffset)
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
          x1 = str(x1f + cols * coloffset - coloffset)
        else:
          x2 = str(x2f + cols * coloffset - coloffset)
        for y in range(rows):
          y = str(float(y1) + y * rowoffset)
          e = shallowCopy(dstplain, elem)
          e.set('x1', x1)
          e.set('x2', x2)
          e.set('y1', y)
          e.set('y2', y)
    else:
      for x in range(cols):
        for y in range(rows):
          offsetCopy(dstplain, elem, x, y, False)

def panelize(src):
  eagle = src.getroot()
  if eagle.tag != 'eagle':
    raise 'XML %s not supported.' % eagle.tag

  dsteagle = etree.Element('eagle')
  for k, v in eagle.items():
    dsteagle.set(k, v)
  dst = etree.ElementTree(dsteagle)

  partnames = etree.Element('partnames')

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
              copyPlain(dstplain, child)

            elif child.tag == 'elements':
              elements = child
              dstelements = shallowCopy(dstboard, child)
              for x in range(cols):
                for y in range(rows):
                  for element in elements:
                    offsetCopy(dstelements, element, x, y, False)

                    # Save <attribute> for later addition to <plain>
                    attribute = element.find('attribute')
                    if attribute != None:
                      partname = etree.SubElement(partnames, 'text')
                      partname.text = element.get('name')
                      for k, v in attribute.items():
                        if k == 'x':
                          partname.set(k, str(float(v) + x * coloffset))
                        elif k == 'y':
                          partname.set(k, str(float(v) + y * rowoffset))
                        elif k != 'name':
                          partname.set(k, v)

            elif child.tag == 'signals':
              signals = child
              dstsignals = shallowCopy(dstboard, child)
              for x in range(cols):
                for y in range(rows):
                  for signal in signals:
                    offsetCopy(dstsignals, signal, x, y, True)

            else:
              dstboard.append(child)
        else:
          dstdrawing.append(child)
    else:
      dsteagle.append(child)

  if dstplain != None:
    for elem in partnames:
      dstplain.append(elem)

  return dst

def main():
  argparser = argparse.ArgumentParser(
      description='Panelizer for EAGLE CAD brd file.')
  argparser.add_argument('--cols', type=int, required=True,
      help='Number of colmns (integer).')
  argparser.add_argument('--rows', type=int, required=True,
      help='Number of rows (integer).')
  argparser.add_argument('--coloffset', type=float,
      help='Column offset width in mm (float).')
  argparser.add_argument('--rowoffset', type=float,
      help='Row offset height in mm (float).')
  argparser.add_argument('--stdout', action='store_true', default=False,
      help='Write to stdout instead of file.')
  argparser.add_argument('file', type=str, nargs='+',
      help='EAGLE CAD brd file to process.')

  args = argparser.parse_args()
  global cols, rows, coloffset, rowoffset
  cols = args.cols
  rows = args.rows
  if args.coloffset:
    coloffset = args.coloffset
  if args.rowoffset:
    rowoffset = args.rowoffset

  if cols < 1 or rows < 1:
    print 'cols or rows not properly set.'
    sys.exit(1)
  if coloffset <= 0.0 or rowoffset <= 0.0:
    print 'coloffset or rowoffset not properly set.'
    sys.exit(1)

  for fname in args.file:
    if fname == '-':
      infile = sys.stdin
      args.stdout = True
    else:
      infile = fname

    xmlparser = etree.XMLParser(remove_blank_text=True)
    src = etree.parse(infile, xmlparser)
    dst = panelize(src)

    if args.stdout:
      out = sys.stdout
    else:
      a = fname.rsplit('.', 1) + ['']
      out = open('%s-panel.%s' % (a[0], a[1]), 'w+') # raise

    out.write(
      etree.tostring(
        dst, encoding='UTF-8', xml_declaration=True,
        pretty_print=True
      )
    )

if __name__ == '__main__':
  main()
