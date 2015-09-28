#!/usr/bin/env python
# -*- coding: utf-8 -*-

__description__ = 'Borrado de adjuntos JIRA de todas las incidencias de un ' \
        'determinado proyecto mas antiguas que un numero de dias dado'
__version__ = '0.9.1'
__author__  = 'daniel.faba'


import os
import json
import time
import socket
import zipfile
import argparse
import logging
from logging.handlers import RotatingFileHandler

import Configuration
import JiraApiClient
from View import ViewPort
from View import zipAndMailLog


###############################################################################

LOGLEVEL   = logging.INFO

###############################################################################

config   = None
viewport = None

###############################################################################

class Attachment():
	def __init__(self, id, filename, size):
		self.id = id
		self.filename = filename
		self.size = size
		self.deleted = False
		logging.debug("Adjunto: id=[%s], fichero=[%s]" % (self.id, self))

	def delete(self):
		self.deleted = JiraApiClient.delete('attachment/%s' % self.id)
		if not self.deleted:
			msg = "No se borra adjunto: id=[%s], fichero=[%s]" % (self.id, self)
			logging.error(msg)
			viewport.update(message=msg)

	def isDeleted(self):
		return self.deleted
	
	def __str__(self):
		return self.filename

###############################################################################

class Issue():
	def __init__(self, id,viewport):
		self.id  = id
		self.key = None
		self.attchs = []
		self.project = None
		self.viewport = viewport

		jsondata = JiraApiClient.get('issue/%s' % self.id)
		if jsondata:
			self.key = jsondata['key']
			self.project = jsondata['fields']['project']['key']
			msg = "Leida issue: id=[%s], key=[%s]" % (self.id, self)
			logging.info(msg)
			self.viewport.update(message=msg)
			for e in jsondata['fields']['attachment']:
				self.attchs.append(Attachment(e['id'], e['filename'], e['size']))
		else:
			msg = "Error recuperando issue: [%s]" %self.id
			logging.error(msg)
			self.viewport.update(message=msg)

	def deleteAttachments(self):
		numdel  = 0
		sizedel = 0
		for a in self.attchs:
			a.delete()
			if a.isDeleted():
				numdel  += 1
				sizedel += a.size
				msg = "Borrado adjunto: %s (id: %s)" % (a, a.id)
				logging.info(msg)
				self.viewport.update(message=msg)

			else:
				msg = "Error borrando : %s (id: %s)" % (a, a.id)
				logging.error(msg)
				self.viewport.update(message=msg)

		return numdel, sizedel

	def putComment(self): 
		str_msg = config.get('COMMENT') + "\n\nBorrados:\n{noformat}"
		found = False
		for a in self.attchs:
			if a.isDeleted():
				found = True
				str_msg += "- \%s\%s\%s" % (self.project, self.key, a) + "\n"

		str_msg += "{noformat}"
		dict_msg = {'update':{'comment':[{'add': {'body': str_msg}}]}}
		if found:
			if not JiraApiClient.put("issue/%s" % self.id, dict_msg):
				msg = "No se pudo agregar comentario a " + self.key
				logging.error(msg)
				self.viewport.update(message=msg)

		else:
			msg = "No se escribe comentario porque no se borraron adjuntos"
			logging.error(msg)
                        self.viewport.update(message=msg)


	def isValid(self):
		return (self.key != '')

	def getNumAttachments(self):
		return len(self.attchs)

	def __str__(self):
		return self.key

##############################################################################

def searchIssues(jql, startidx, max):
	params = {
		"jql": jql,
		"startAt": startidx,
		"maxResults": max
	}
	jsonobj = JiraApiClient.get('search', params)
	if jsonobj:
		res = []
		for elem in jsonobj['issues']:
			res.append(elem['id'])
		msg = "Encontrados %s resultados" % len(res)
		logging.info(msg)
		return res, jsonobj['total']
	else:
		msg = "Error recuperando issues"
		logging.error(msg)
		return None, None


def showSummary(msg, secs, nissues, ndel, nerr, tsize, logfile):
	lines = [
		"Terminado - Procesadas %s issues en %.2f segundos." % (nissues, secs),
		"Adjuntos eliminados: %s. Errores: %s." % (ndel, nerr),
		"Se han liberado: %.2f MB" % tsize
	]

	[logging.info(x) for x in lines]

	message =  "\n".join(lines)
	print "\n" + message + "\n" 
	subject = 'Limpieza de adjuntos JIRA'
	try:
		zipAndMailLog(logfile, config.get('SMTP_SERVER'), subject, msg + "\n" + message, 
				config.get('NOTIFY_EMAILS'), config.get('SMTP_FROM'),
				config.get('SMTP_PASS'), config.get('SMTP_PORT'))
	except Exception as e:
		print "Error enviando mail: %s" % e
		logging.error("Error enviando mail: %s" % e)


def doTheMutilation(jql, msg, logfile):
	numdel  = 0
	numerr  = 0
	elapsed = 0
	cur  = 0
	sizedel = float(0)
	bsize   = config.get('BLOCKSIZE')
	max_errors = config.get('MAX_ERRORS')

	(issues, numtotal) = searchIssues(jql, 0, bsize)

	if numtotal:
		try:
			header = msg + ' '*9 + '^C para cancelar'
			viewport = ViewPort(maxval=numtotal, header=header, fullscr=True)
			logging.info("Procesando en bloques de %s" % bsize)
			viewport.update(0, "Procesando en bloques de %s" % bsize)

			
			while issues and len(issues) and (numerr < max_errors):
				for issue in issues:
					issue = Issue(issue,viewport)
					if numerr == max_errors: break
					if issue.key is not None:
						res_num, res_size = issue.deleteAttachments()
						numdel += res_num
						sizedel += float(res_size)/(2**20)
						issue.putComment()
						if res_num < issue.getNumAttachments():
							numerr += issue.getNumAttachments() - res_num
						if (cur > numtotal): cur = numtotal
						viewport.update(cur)
						cur += 1
					else:
						numerr += 1

				(issues, nothing) = searchIssues(jql, 0, bsize)
				if issues and len(issues):
					logging.info("Pausa de %s segundos" % 5)
					viewport.update(cur, "Pausa de %s segundos" % 5)
					time.sleep(5) # rest a while

			viewport.finish()
			elapsed = viewport.pbar.seconds_elapsed

		except KeyboardInterrupt:
			logging.info("!!!Interrumpido!!! (sigint)")
			print "\n\n!!!Interrumpido!!! (sigint)\n"

		if numerr == max_errors:
			mes = u"Interrumpido! -> Se ha alcanzado en maximo de errores permitidos (%s)." % max_errors
			logging.error(mes)
			print("\n\n" + 	mes + "\n")	

	showSummary(msg, elapsed, cur, numdel, numerr, sizedel, logfile)


def init_argparse():
        parser = argparse.ArgumentParser(version=__version__,
                        description=__description__)

        parser.add_argument('project', type=str,
                help='ID del proyecto de JIRA')
        parser.add_argument('ndays', type=int,
                help='Cerradas hace mas de "ndays" dias')

        return parser.parse_args()


def init_logging():
	logpath = os.path.dirname(os.path.abspath(__file__))
	logfile = logpath + '/logs/' + os.path.basename(__file__).replace('.py', '.log')

	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	handler = RotatingFileHandler(logfile, backupCount=9)
	handler.setFormatter(formatter)

	logger = logging.getLogger()
	logger.setLevel(LOGLEVEL)
	logger.addHandler(handler)

	if not os.path.exists(logpath): os.makedirs(logpath)
	# force rotate on each program run
	if os.path.isfile(logfile):
		logger.handlers[0].doRollover()

	hostname = socket.gethostname()
	hostname += " (%s)" % socket.gethostbyname(hostname)
	msg="Inicio - %s en %s" % (__file__, hostname)
	logging.info(msg)

	return logfile


def main():
	args = init_argparse()
	logfile = init_logging()

	global config
	try:
		config = Configuration.Config(__file__)
		JiraApiClient.configure(config=config)
		
	except Exception, e:
		print u"%s" % e
		logging.error(u"%s" % e)
	else:
		msg_job = u"Trabajo: Cerradas hace más de %s días, proyecto %s."\
				% (args.ndays, args.project)

		jql = "project = %s AND resolved <= -%sd AND attachments IS NOT" \
				" EMPTY ORDER BY created ASC" % (args.project, args.ndays)
		#print jql

		logging.info(msg_job)
		doTheMutilation(jql, msg_job, logfile)


if __name__ == "__main__":
	main()
