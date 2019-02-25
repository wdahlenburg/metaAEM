#!/bin/python

from bs4 import BeautifulSoup
import requests
import sys
import urllib.parse
import tempfile
import subprocess
import time

validPathTypes = ["sling:Folder", "sling:OrderedFolder", "nt:folder", "nt:unstructured", "cq:Page", "cq:PageContent"]
validContentTypes = ["dam:Asset"]
metaDataFiles = {}

userMetaDataCriteria = ["jcr:createdBy", "jcr:lastModifiedBy", "cq:lastModifiedBy", "cq:lastPublishedBy", "cq:lastReplicatedBy"]
userMetaData = []

s = requests.Session()

def checkContentExplorer(baseUrl):
	url = baseUrl + "/crx/explorer/browser/index.jsp"
	
	resp = s.get(url)
	if resp.status_code == 200:
		return True
	else:
		print("CRX not found. Status Code: %d" % (resp.status_code))
		return False

def getTree(baseUrl, path):
	url = baseUrl + "/crx/explorer/browser/tree.jsp?Path=" + path + "&_charset_=utf-8"
	resp = s.get(url)
	if resp.status_code == 200:
		soup = BeautifulSoup(resp.text, 'html.parser')
		paths = soup.find_all("span", {"class": "nodeName"})
		values = []
		for i in paths:
			if not i.text.startswith("/"):
				values.append("/" + i.text)
			else:
				values.append(i.text)

		return values
	else:
		print("Not able to lookup data")

def recursiveLookup(baseUrl, path, retries=3):
	print("Searching through %s" % path)
	url = baseUrl + "/crx/explorer/browser/content.jsp?Path=" + urllib.parse.quote_plus(path) + "&_charset_=utf-8"

	try:
		resp = s.get(url)
		if resp.status_code == 200:
			soup = BeautifulSoup(resp.text, 'html.parser')
			rows = soup.find_all("tr")
			values = []
			for rowVal in rows[1:]:

				# Check if user metadata exists
				nodeName = rowVal.find_all("td")[1].text
				if nodeName in userMetaDataCriteria:
					nodeValue = rowVal.find_all("td")[3].text
					if nodeValue not in userMetaData:
						userMetaData.append(nodeValue)

				# Check if file is a validContentType
				nodeType = rowVal.find_all("td")[2].text
				if nodeType in validContentTypes:
					# Download file and scrape metadata
					fileLocation = rowVal.find_all("td")[0].find("img").attrs["alt"]
					metaDataFiles[fileLocation] = nodeName
					print("Downloading: %s" % (nodeName))


				# Recursive Search
				nodeType = rowVal.find_all("td")[2].text
				if nodeType in validPathTypes:
					nodeName = rowVal.find_all("td")[0].find("img").attrs['alt']
					if not nodeName.startswith("/"):
						queryPath = "/" + nodeName
					else:
						queryPath = nodeName

					# Ensure we don't look back at ourselves
					if queryPath != path:
						recursiveLookup(baseUrl, queryPath)
		else:
			print("Not able to lookup data")
	except:
		if retries == 0:
			return
		else:
			time.sleep(5)
			recursiveLookup(baseUrl, path, retries - 1)

def dumpMetadata(baseUrl, files):
	for file in files.keys():
		temp = tempfile.NamedTemporaryFile()
		url = baseUrl + file
		resp = s.get(url)
		temp.write(resp.content)
		command = ["/usr/bin/exiftool", temp.name]
		proc = subprocess.Popen(command, stdout=subprocess.PIPE)
		output = proc.stdout.read()
		print("="*25)
		results = ouput.decode("utf-8")
		results = results.replace(temp.name.split('/')[-1], files[file])
		results = results.replace('/tmp', "/".join(file.split("/")[:-1]) + "/")
		print(results)
		temp.close()

def main():
	if len(sys.argv) != 2:
		print("Usage: python3 ./metaAEM.py https://mydomain.com")
		sys.exit(0)

	baseUrl = str(sys.argv[1])
	if checkContentExplorer(baseUrl):
		recursiveLookup(baseUrl, "/")

		if len(userMetaData) > 0:
			print("Users:")
			for user in userMetaData:
				print(user)

		dumpMetadata(baseUrl, metaDataFiles)
main()
