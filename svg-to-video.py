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
	writeFrames(filename, duration, framerate, outDir, frames, digit_length)
	compileVideo(outDir, framerate, digit_length)

def writeFrames(filename, duration, framerate, outDir, frames, digit_length):
	tree = ET.parse(filename)
	root = tree.getroot()

	if ("svg" not in root.tag):
		print("This script only works on svg files.")
		exit()

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
	attributeName = tag.attrib['attributeName']
	beginList = [0]
	if 'begin' in tag.attrib:
		beginList = parseBeginValue(tag.attrib['begin'])
	dur = parseClockValue(tag.attrib['dur'])
	repeatDur = dur
	if 'repeatDur' in tag.attrib:
		if tag.attrib['repeatDur'] == "indefinite":
			repeatDur = None
		else:
			repeatDur = parseClockValue(tag.attrib['repeatDur'])
	elif 'repeatCount' in tag.attrib:
		if tag.attrib['repeatCount'] == "indefinite":
			repeatDur = None
		else:
			repeatDur = dur*float(tag.attrib['repeatCount'])
	
	nonfutureBeginList = [b for b in beginList if b <= time]
	if len(nonfutureBeginList) == 0:
		return
	
	begin = max(nonfutureBeginList)
	
	if repeatDur is not None and time > begin + repeatDur:
		if 'fill' in tag.attrib and tag.attrib['fill'] == 'freeze':
			element.attrib[attributeName] = tag.attrib['to']
		return
	
	fromArr = parseValue(tag.attrib['from'])
	toArr = parseValue(tag.attrib['to'])
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
	attributeName = tag.attrib['attributeName']
	begin = 0
	if 'begin' in tag.attrib:
		begin = parseClockValue(tag.attrib['begin'])
	dur = None
	if 'dur' in tag.attrib:
		dur = parseClockValue(tag.attrib['dur'])
	
	if time < begin or (dur is not None and time > begin + dur):
		return
	
	element.attrib[attributeName] = str(tag.attrib['to'])

def processAnimateTransformTag(element, tag, time):
	attributeName = tag.attrib['attributeName']
	type = tag.attrib['type']
	begin = 0
	if 'begin' in tag.attrib:
		begin = parseClockValue(tag.attrib['begin'])
	dur = parseClockValue(tag.attrib['dur'])
	repeatDur = dur
	if 'repeatDur' in tag.attrib:
		if tag.attrib['repeatDur'] == "indefinite":
			repeatDur = None
		else:
			repeatDur = parseClockValue(tag.attrib['repeatDur'])
	elif 'repeatCount' in tag.attrib:
		if tag.attrib['repeatCount'] == "indefinite":
			repeatDur = None
		else:
			repeatDur = dur*float(tag.attrib['repeatCount'])
	
	if time < begin:
		return
	if repeatDur is not None and time > begin + repeatDur:
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