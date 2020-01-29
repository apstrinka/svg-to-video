import cairosvg
import copy
import math
import os
import sys
import xml.etree.ElementTree as ET

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
	subvalues = value.replace(',', ' ').split()
	return [float(i) for i in subvalues]

def parseClockValue(value):
	#Currently only time values in the form "12.3s" supported
	return float(value[:-1])

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