import cairosvg
import copy
import math
import os
import sys
import xml.etree.ElementTree as ET

class Color:
	def __init__(self, red, green, blue, alpha):
		self.red = red
		self.green = green
		self.blue = blue
		self.alpha = alpha
	
	def __str__(self):
		return "rgba(" + str(self.red) + "," + str(self.green) + "," + str(self.blue) + "," + str(self.alpha) + ")"

def main():
	if len(sys.argv) < 4:
		print("Usage: python svg-to-video.py (filename) (duration in seconds) (framerate in frames/second)")
		exit()
	filename = sys.argv[1]
	duration = float(sys.argv[2])
	framerate = float(sys.argv[3])
	outDir = filename[:-4]
	print(outDir)
	frames = int(framerate * duration)
	digit_length = len(str(frames))
	tree = ET.parse(filename)
	preprocessTree(tree)
	writeFrames(filename, tree, duration, framerate, outDir, frames, digit_length)
	compileVideo(outDir, framerate, digit_length)

def preprocessTree(tree):
	root = tree.getroot()
	
	if ("svg" not in root.tag):
		print("This script only works on svg files.")
		exit()
	
	animationElements = getAnimationElements(root, {})
	for element in animationElements.values():
		preprocessAnimationElement(element, animationElements)

def getAnimationElements(element, dict):
	for child in element:
		if child.tag in ["{http://www.w3.org/2000/svg}animate", "{http://www.w3.org/2000/svg}set","{http://www.w3.org/2000/svg}animateTransform"]:
			id = child.get("id", len(dict))
			dict[id] = child
		getAnimationElements(child, dict)
	return dict

def preprocessAnimationElement(element, animationElements):
	preprocessBeginAttribute(element, animationElements)
	preprocessDurAttribute(element)
	preprocessRepeatDurAttribute(element)
	preprocessFromAttribute(element)
	preprocessToAttribute(element)

def preprocessBeginAttribute(element, animationElements):
	beginAttribute = element.get('begin')
	begin = [0]
	if beginAttribute is not None:
		begin = parseBeginValue(beginAttribute)
	element.set('begin', begin)

def preprocessDurAttribute(element):
	durAttribute = element.get('dur')
	dur = 'indefinite'
	if durAttribute is not None and durAttribute != 'indefinite':
		dur = parseClockValue(durAttribute)
	element.set('dur', dur)

def preprocessRepeatDurAttribute(element):
	repeatDurAttribute = element.get('repeatDur')
	repeatCountAttribute = element.get('repeatCount')
	dur = element.get('dur')
	repeatDur = dur
	if repeatDurAttribute is not None:
		if repeatDurAttribute == 'indefinite':
			repeatDur = 'indefinite'
		else:
			repeatDur = parseClockValue(repeatDurAttribute)
	elif repeatCountAttribute is not None:
		if repeatCountAttribute == 'indefinite':
			repeatDur = 'indefinite'
		else:
			repeatDur = dur*float(repeatCountAttribute)
	element.set('repeatDur', repeatDur)

def preprocessFromAttribute(element):
	fromAttribute = element.get('from')
	element.set('from', parseValue(fromAttribute))

def preprocessToAttribute(element):
	toAttribute = element.get('to')
	element.set('to', parseValue(toAttribute))

def parseValue(value):
	if value.startswith("rgba("):
		subvalues = value[4:-1].replace(',', ' ').split()
		return Color(float(subvalues[0]), float(subvalues[1]), float(subvalues[2]), float(subvalues[3]))
	if value.startswith("rgb("):
		subvalues = value[4:-1].replace(',', ' ').split()
		print(subvalues)
		return Color(float(subvalues[0]), float(subvalues[1]), float(subvalues[2]), 100.0)
	if value.startswith("#"):
		if len(value) == 4:
			return Color(float(int(value[1], 16)*16), float(int(value[2], 16)*16), float(int(value[3], 16)*16), 100.0)
		if len(value) == 7:
			return Color(float(int(value[1:3], 16)), float(int(value[3:5], 16)), float(int(value[5:7], 16)), 100.0)
		if len(value) == 9:
			return Color(float(int(value[3:5], 16)), float(int(value[5:7], 16)), float(int(value[7:9], 16)), float(int(value[3:5], 16))*100/255)
	subvalues = value.replace(',', ' ').split()
	return [float(i) for i in subvalues]

def parseBeginValue(value):
	values = value.split(';')
	return [parseClockValue(v) for v in values]

def parseClockValue(value):
	components = value.split(':')
	if len(components) == 3:
		hours = int(components[0])
		minutes = int(components[1])
		seconds = float(components[2])
		return 3600*hours + 60*minutes + seconds
	if len(components) == 2:
		minutes = int(components[0])
		seconds = float(components[1])
		return 60*minutes + seconds
		
	if value.endswith('ms'):
		return float(value[:-2])/1000
	if value.endswith('s'):
		return float(value[:-1])
	if value.endswith('min'):
		return 60*float(value[:-3])
	if value.endswith('h'):
		return 3600*float(value[:-1])
	return float(value)

def writeFrames(filename, tree, duration, framerate, outDir, frames, digit_length):
	root = tree.getroot()

	if not os.path.exists(outDir):
		os.mkdir(outDir)

	for i in range(frames+1):
		time = i / framerate
		filename = outDir + "/" + str(i).zfill(digit_length)
		if i % 50 == 0:
			print("Processing frame " + str(i))
		writeFrame(tree, time, filename)

def writeFrame(tree, time, filename):
	copied = copy.deepcopy(tree)
	processElement(copied.getroot(), time)
	copied.write(filename + ".svg")
	cairosvg.svg2png(url=filename+".svg", write_to=filename+".png")

def processElement(element, time):
	for child in element[:]:
		if child.tag == "{http://www.w3.org/2000/svg}animate":
			element.remove(child)
			processAnimateTag(element, child, time)
		elif child.tag == "{http://www.w3.org/2000/svg}set":
			element.remove(child)
			processSetTag(element, child, time)
		elif child.tag == "{http://www.w3.org/2000/svg}animateTransform":
			element.remove(child)
			processAnimateTransformTag(element, child, time)
		else:
			processElement(child, time)

def processAnimateTag(element, tag, time):
	attributeName = tag.get('attributeName')
	beginList = tag.get('begin')
	dur = tag.get('dur')
	repeatDur = tag.get('repeatDur')
	
	nonfutureBeginList = [b for b in beginList if b <= time]
	if len(nonfutureBeginList) == 0:
		return
	
	begin = max(nonfutureBeginList)
	
	if repeatDur != 'indefinite' and time > begin + repeatDur:
		if 'fill' in tag.attrib and tag.attrib['fill'] == 'freeze':
			element.attrib[attributeName] = tag.attrib['to']
		return
	
	fromArr = tag.get('from')
	toArr = tag.get('to')
	t = time - begin
	while t > dur:
		t = t - dur
	t = t/dur
	interpolated = interpolate(fromArr, toArr, t)
	if isinstance(interpolated, Color):
		element.attrib[attributeName] = str(interpolated)
	else:
		element.attrib[attributeName] = ' '.join(interpolated)

def processSetTag(element, tag, time):
	attributeName = tag.get('attributeName')
	beginList = tag.get('begin')
	dur = tag.get('dur')
	
	nonfutureBeginList = [b for b in beginList if b <= time]
	if len(nonfutureBeginList) == 0:
		return
	
	begin = max(nonfutureBeginList)
	
	if dur != 'indefinite' and time > begin + dur:
		return
	
	element.attrib[attributeName] = str(tag.attrib['to'])

def processAnimateTransformTag(element, tag, time):
	attributeName = tag.get('attributeName')
	beginList = tag.get('begin')
	dur = tag.get('dur')
	repeatDur = tag.get('repeatDur')
	
	nonfutureBeginList = [b for b in beginList if b <= time]
	if len(nonfutureBeginList) == 0:
		return
	
	begin = max(nonfutureBeginList)
	
	if repeatDur != 'indefinite' and time > begin + repeatDur:
		if 'fill' in tag.attrib and tag.attrib['fill'] == 'freeze':
			element.attrib[attributeName] = tag.attrib['to']
		return
	
	fromArr = parseValue(tag.attrib['from'])
	toArr = parseValue(tag.attrib['to'])
	t = time - begin
	while t > dur:
		t = t - dur
	t = t/dur
	interpolated = interpolateValueArray(fromArr, toArr, t)
	element.attrib[attributeName] = type + '(' + ' '.join(interpolated) + ')'

def interpolate(fromValue, toValue, t):
	if isinstance(fromValue, Color):
		return interpolateColor(fromValue, toValue, t)
	else:
		return interpolateValueArray(fromValue, toValue, t)

def interpolateColor(fromColor, toColor, t):
	r = interpolateSingleValue(fromColor.red, toColor.red, t)
	g = interpolateSingleValue(fromColor.green, toColor.green, t)
	b = interpolateSingleValue(fromColor.blue, toColor.blue, t)
	a = interpolateSingleValue(fromColor.alpha, toColor.alpha, t)
	return Color(r, g, b, a)

def interpolateValueArray(fromArr, toArr, t):
	retArr = []
	for i in range(len(fromArr)):
		fromVal = fromArr[i]
		toVal = 0
		if i < len(toArr):
			toVal = toArr[i]
		retArr.append(str(interpolateSingleValue(fromVal, toVal, t)))
	return retArr

def interpolateSingleValue(fromVal, toVal, t):
	delta = toVal - fromVal
	return t*delta + fromVal

def compileVideo(outDir, framerate, digit_length):
	os.system('ffmpeg -f image2 -r ' + str(framerate) + ' -start_number ' + '0'*digit_length + ' -i ' + outDir + '\%0' + str(digit_length) + 'd.png -vcodec mpeg4 -q:v 0 -y ' + outDir + '.mp4')

main()