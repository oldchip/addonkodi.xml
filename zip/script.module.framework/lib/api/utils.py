import os
import sys
import time
import mimetypes
import hashlib
import urllib
import base64

_urllib_quote = urllib.quote
_urllib_quote_plus = urllib.quote_plus


def makedirs(path):
  if not os.path.exists(path):
    os.makedirs(path)

def timestamp_from_datetime(dt):
  return time.mktime(dt.timetuple())

def guess_mime_type(filename):
  mtype = mimetypes.guess_type(filename)[0]
  if mtype: return mtype
  else: return 'application/octet-stream'

def urlencode(string):
  encoded = urllib.urlencode({'v':string})
  return encoded[2:]

def unistr(s):
  if isinstance(s, unicode):
    s = s.encode('raw_unicode_escape', 'strict')
  return s

def quote(s, *args, **kwargs):
  return _urllib_quote(unistr(s), *args, **kwargs)

def quote_plus(s, *args, **kwargs):
  return _urllib_quote_plus(unistr(s), *args, **kwargs)

def safe_encode(string):
  return base64.b64encode(string).replace('/','@').replace('+','*').replace('=','_')

def safe_decode(string):
  return base64.b64decode(string.replace('@','/').replace('*','+').replace('_','=') + '=' * (4 - len(string) % 4))


# Test for common truth values
def is_true(value):
  return value in (True, 1, 'true', 'True')


# using module re to pluralize most common english words
# (rule_tuple used as function default, so establish it first)

import re, string


def clean_up_string(s):
  s = unicode(s)

  # Ands.
  s = s.replace('&', 'and')

  # Pre-process the string a bit to remove punctuation.
  s = re.sub('[' + string.punctuation + ']', '', s)

  # Lowercase it.
  s = s.lower()

  # Strip leading "the/a"
  s = re.sub('^(the|a) ', '', s)

  # Spaces.
  s = re.sub('[ ]+', ' ', s).strip()

  return s



urllib.quote = quote
urllib.quote_plus = quote_plus


def ps_import(name):
  """
    Platform-specific import function - imports bundled "name_new" modules when targeting
    Python on OS X or Linux.
  """
  try:
    if sys.platform != 'win32':
      mod = __import__(name + '_new')
      return mod
  except:
    pass
  return __import__(name)
