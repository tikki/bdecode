# encoding: utf-8

def bdecode(data):
	'''decode bencoded data to python objects'''
	return _dechunk(data, 0)[0]

def _dechunk(data, i):
	c = data[i]
	i += 1
	# check for known data types (dict, list, integer, string)
	if c == 'd':
		o = {}
		while 1:
			k, i = _dechunk(data, i)
			v, i = _dechunk(data, i)
			o[k] = v
			if data[i] == 'e':
				return o, i + 1
	elif c == 'l':
		o = []
		while 1:
			e, i = _dechunk(data, i)
			o.append(e)
			if data[i] == 'e':
				return o, i + 1
	elif c == 'i':
		o = ''
		while 1:
			if data[i] == 'e':
				return int(o), i + 1
			o += data[i]
			i += 1
	elif c.isdigit():
		# get the string size
		e = data.find(':', i)
		l = int(data[i - 1:e]) # - 1 because of the initial increment at the beginning of dechunk
		# calc string boundaries
		s = e + 1
		# read data
		return data[s:s + l], s + l
	raise 'unknown data type'

def _main():
	import sys, os
	try:
		fn = sys.argv[1]
		with open(fn, 'rb') as fo:
			info = bdecode(fo.read())['info']
			print 'name:', info['name']
			print 'files:'
			for file in info['files']:
				print '\t', os.path.join(*file['path'])
	except:
		print 'Usage:', sys.argv[0], 'filename.torrent'

if __name__ == '__main__':
	_main()
