# -*- coding: utf-8 -*-

__author__  = 'daniel.faba'

import os
import codecs
from ConfigParser import SafeConfigParser


class Config(object):
	_instance = None
	
	cfg_vals = {}

	def __new__(cls, *args, **kwargs):
		if not cls._instance:
			cls._instance = super(Config, cls).__new__(cls, *args, **kwargs)
		return cls._instance


	def __init__(self, prog_filename):
		fn = os.path.splitext(os.path.abspath(prog_filename))[0] + '.ini'
		if not os.access(fn, os.R_OK):
			raise ConfigException("No se puede leer %s" % fn)

		self.parser = SafeConfigParser()
		try:
			codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)
			fp = codecs.open(fn, 'r', encoding='utf-8')
			self.parser.readfp(fp)
		except:
			raise ConfigException(u"Fichero de configuración debe ser UTF-8: %s" % fn)

		self.__populate()


	def __populate(self):
		def isEmpty(str):
			if str is None or str == '': return True
			return False

		self.cfg_vals['JIRA_URL' ] = self.parser.get('jira_server', 'jira_url')
		self.cfg_vals['JIRA_USER'] = self.parser.get('jira_server', 'jira_user')
		self.cfg_vals['JIRA_PASS'] = self.parser.get('jira_server', 'jira_pass')
		self.cfg_vals['COMMENT'  ] = self.parser.get('settings', 'comment')
		self.cfg_vals['BLOCKSIZE'] = self.parser.get('settings', 'blocksize')
		self.cfg_vals['MAX_ERRORS'] = self.parser.get('settings', 'max_errors')
		self.cfg_vals['NOTIFY_EMAILS'] = self.parser.get('settings', 'notify_emails').split()
		self.cfg_vals['SMTP_SERVER'] = self.parser.get('settings', 'smtp_server')
		self.cfg_vals['SMTP_FROM'] = self.parser.get('settings', 'smtp_from')
		self.cfg_vals['SMTP_PASS'] = self.parser.get('settings', 'smtp_pass')
		self.cfg_vals['SMTP_PORT'] = self.parser.get('settings', 'smtp_port')

		for k, v in self.cfg_vals.items():
			if isEmpty(v):
				raise ConfigException("El valor de \'%s\' no se ha definido." % k.lower())

		try:
			self.cfg_vals['BLOCKSIZE'] = int(self.cfg_vals['BLOCKSIZE'])
			self.cfg_vals['MAX_ERRORS'] = int(self.cfg_vals['MAX_ERRORS'])	 
		except Exception:
			raise ConfigException(u"El valor de configuración de 'blocksize' o 'max_errors' no es entero.")


	def get(self, key):
		return self.cfg_vals[key]


class ConfigException(Exception):
	pass
