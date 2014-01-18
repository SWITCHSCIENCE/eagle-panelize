#!/usr/bin/python

from lxml import etree
import sys

cols = 5
rows = 3
coloffset = 35 # mm
rowoffset = 50 # mm

# Copy src as child of dst.
def shallowCopy(dst, src):
  elem = etree.SubElement(dst, src.tag)
  for k, v in src.items():
    elem.set(k, v)
  return elem

# Copy src as child of dst.
def offsetCopy(dst, src, x, y):
  elem = etree.SubElement(dst, src.tag)
  for k, v in src.items():
    if k == 'name' and elem.tag != 'attribute':
      elem.set(k, '%s-%d-%d' % (v, x, y))
    elif k == 'element':
      elem.set(k, '%s-%d-%d' % (v, x, y))
    elif k in ['x', 'x1', 'x2']:
      elem.set(k, str(float(v) + x * coloffset))
    elif k in ['y', 'y1', 'y2']:
      elem.set(k, str(float(v) + y * rowoffset))
    else:
      elem.set(k, v)
  for child in src:
    offsetCopy(elem, child, x, y)
  return elem

# Copy children of src as children of dst.
def offsetCopyChildren(dst, src):
  for x in range(cols):
    for y in range(rows):
      for elem in src:
        offsetCopy(dst, elem, x, y)

src = etree.parse(sys.stdin)
eagle = src.getroot()
if eagle.tag != 'eagle':
  raise 'XML %s not supported.' % eagle.tag

dsteagle = etree.Element('eagle', version=eagle.get('version'))
dst = etree.ElementTree(dsteagle)

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
            offsetCopyChildren(shallowCopy(dstboard, child), child)
          elif child.tag == 'elements':
            offsetCopyChildren(shallowCopy(dstboard, child), child)
          elif child.tag == 'signals':
            offsetCopyChildren(shallowCopy(dstboard, child), child)
          else:
            dstboard.append(child)
      else:
        dstdrawing.append(child)
  else:
    dsteagle.append(child)

print etree.tostring(
    dst, encoding='UTF-8', xml_declaration=True,
    pretty_print=True)
