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

# Copy children of src as children of dst.
def offsetCopyChildren(dst, src, recursive):
  for x in range(cols):
    for y in range(rows):
      for elem in src:
        offsetCopy(dst, elem, x, y, recursive)

parser = etree.XMLParser(remove_blank_text=True)
src = etree.parse(sys.stdin, parser)
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
            offsetCopyChildren(dstplain, child, False)
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
                      elif k == 'name':
                        pass
                      else:
                        partname.set(k, v)

          elif child.tag == 'signals':
            offsetCopyChildren(shallowCopy(dstboard, child), child, True)
          else:
            dstboard.append(child)
      else:
        dstdrawing.append(child)
  else:
    dsteagle.append(child)

if dstplain != None:
  for elem in partnames:
    dstplain.append(elem)

print etree.tostring(
    dst, encoding='UTF-8', xml_declaration=True,
    pretty_print=True)
