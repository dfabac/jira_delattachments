
__author__  = 'daniel.faba'

import requests
import json
import logging

api_url = ''
credentials = ''

logging.getLogger("requests").setLevel(logging.ERROR)

###############################################################################

def configure(jiraurl=None, user=None, passw=None, config=None):
	global api_url
	global credentials
	if config:
		strurl  = config.get('JIRA_URL') + "/rest/api/latest/"
		struser = config.get('JIRA_USER')
		strpass = config.get('JIRA_PASS')
	else:
		strurl  = jiraurl
		struser = user
		strpass = passw
	if not(strurl and struser and strpass):
		raise JiraApiException('JiraApiClient - Configuracion incompleta o erronea')

	api_url = strurl
	credentials = (struser, strpass)
	logging.info("JiraApiClient configurado OK --> " + strurl)

def isConfigured(fn):
	def new(*args):
		if api_url == '': 
			raise JiraApiException('JiraApiClient no esta configurado')
		return fn(*args)
	return new


###############################################################################

@isConfigured
def get(path, params=None):
	url = api_url + path
	try:
		r = requests.get(url, params=params, auth=credentials, timeout=60)
		if r.status_code == requests.codes.ok:
				return r.json()
		r.raise_for_status()
	except Exception, e:
		logging.error("JiraApiClient GET ERROR: %s" %e)
		return None


@isConfigured
def delete(path):
	url = api_url + path
	try:
		r = requests.delete(url, auth=credentials, timeout=30)
		if r.status_code == 204 : return True
		r.raise_for_status()
	except Exception, e:
		logging.error("JiraApiClient DELETE ERROR: %s" %e)
		return False


@isConfigured
def put(path, payload):
	url = api_url + path
	headers = {'Content-Type': 'application/json'}
	try:
		r = requests.put(url, auth=credentials, data=json.dumps(payload), 
							headers=headers, timeout=30)
		if r.status_code == 204 : return True
		r.raise_for_status()
	except Exception, e:
		logging.error("JiraApiClient PUT ERROR: %s" %e)
		return False

###############################################################################

class JiraApiException(Exception):
	pass