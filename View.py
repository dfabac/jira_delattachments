
__author__  = 'daniel.faba'

import os
import time
import platform
import logging
import smtplib
import zipfile
import tempfile
from email import encoders
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart    
from email.mime.text import MIMEText



class ViewPort:
	def __init__(self, progressbar=True, maxval=100, loglines=5, header=None, fullscr=False):
		self.width = getTerminalSize()[0]
		self.height = getTerminalSize()[1]
		self.__setANSIMode()
		self.started = False

		hsize = 0
		if header: hsize = 3
		if (loglines > (self.height - hsize)) or fullscr:
			loglines = (self.height - hsize)		

		self.logbuffer = []
		for i in range(loglines): self.logbuffer.append('')

		if header:
			print self.__linetrunc(header, self.width)
			print '=' * self.width
		if self.ANSI:
			print "\n"*(loglines-1)

		if progressbar:
			from progressbar import Bar, ETA, Percentage, RotatingMarker, \
					ProgressBar, Counter
			widg = [Counter(), '/%s (' % maxval, Percentage(), ') ',
					RotatingMarker(), ' ', Bar(left='[', right=']'), ETA()]
			self.pbar = ProgressBar(widgets=widg, maxval=maxval)
		else: 
			self.pbar = None


	def update(self, value=None, message=None):

		if not self.started: 
			self.pbar.start()
			self.started = True

		if message and self.ANSI:
			self.logbuffer.append(message)
			self.logbuffer = self.logbuffer[1:]


			print "\033[%sA" % (len(self.logbuffer) + 1)		
			for line in self.logbuffer:
				print("\033[K" + self.__linetrunc(line, self.width))

		if self.pbar: self.pbar.update(value)


	def finish(self, interrupted=False):
		if self.pbar: self.pbar.finish()
		if self.ANSI:
			print "\033[%sB" % (len(self.logbuffer) + 1)


	def setMaxValue(self, val):
		self.pbar.maxval = val


	def __linetrunc(self, line, max):
		return (line[:max-3] + '...') if len(line) > max else line


	def __setANSIMode(self):
		self.ANSI = True
		if platform.system() == 'Windows':
			self.ANSI = False


def getTerminalSize():
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd,termios.TIOCGWINSZ,'1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))
    return int(cr[1]), int(cr[0])



def zipAndMailLog(logfile, mailserver, mailsubject, mailtext, mailto_list, mailfrom, passwd, port):
        pretty_name=os.path.basename(logfile)
        zf = tempfile.TemporaryFile(prefix='mail', suffix='.zip')
        zip = zipfile.ZipFile(zf, 'w')
        zip.write(logfile, arcname=os.path.basename(logfile))
        zip.close()
        zf.seek(0)

        mailmsg = MIMEMultipart()
        mailmsg['Subject'] = mailsubject
        mailmsg['To'] = ', '.join(mailto_list)
        mailmsg['From'] = mailfrom
        msg = MIMEBase('application', 'zip')
        msg.set_payload(zf.read())
        encoders.encode_base64(msg)
        msg.add_header('Content-Disposition', 'attachment',
                filename=os.path.basename(logfile) + '.zip')


        mailmsg.attach(MIMEText(mailtext.encode('utf-8'), 'plain', 'utf-8'))
        mailmsg.attach(msg)

        smtp = smtplib.SMTP(mailserver, int(port))
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(mailfrom, passwd)
        smtp.sendmail(mailfrom, mailto_list, mailmsg.as_string())
        smtp.close()

