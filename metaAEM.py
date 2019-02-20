#!/bin/python

import requests
from bs4 import BeautifulSoup
import urllib.parse

validPathTypes = ["sling:Folder", "sling:OrderedFolder", "nt:folder", "nt:unstructured", "cq:Page", "cq:PageContent"]
validContentTypes = ["dam:Asset"]

userMetaDataCriteria = ["jcr:createdBy", "jcr:lastModifiedBy"]
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
				if nodeType in validContentType:
					# Download file and scrape metadata
					# TODO
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
	except requests.exceptions.SSLError:
		if retries == 0:
			return
		else:
			recursiveLookup(baseUrl, path, retries - 1)

def main():
	baseUrl = "https://s-wcm.dinersclub.com"
	if checkContentExplorer(baseUrl):
		localPaths = getTree(baseUrl, "/")
		for path in localPaths:
			recursiveLookup(baseUrl, path)

	print("Users:")
	for user in userMetaData:
		print(user)
main()