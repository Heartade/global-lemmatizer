import sqlite3
from lxml import etree
import wikitextparser as wtp
import re

conn = sqlite3.connect('forms.db')
cur = conn.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS words (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, language TEXT, UNIQUE(word, language))')
cur.execute('CREATE INDEX IF NOT EXISTS words_word_index ON words (word)')
cur.execute('CREATE INDEX IF NOT EXISTS words_language_index ON words (language)')
cur.execute('CREATE TABLE IF NOT EXISTS lemmas (id INTEGER PRIMARY KEY AUTOINCREMENT, lemma TEXT, language TEXT, UNIQUE(lemma, language))')
cur.execute('CREATE INDEX IF NOT EXISTS lemmas_lemma_index ON lemmas (lemma)')
cur.execute('CREATE INDEX IF NOT EXISTS lemmas_language_index ON lemmas (language)')
cur.execute('CREATE TABLE IF NOT EXISTS word_forms (id INTEGER PRIMARY KEY AUTOINCREMENT, form TEXT, lemma TEXT, type TEXT, language TEXT, UNIQUE(form, lemma, type, language))')
cur.execute('CREATE INDEX IF NOT EXISTS word_forms_form_index ON word_forms (form)')
cur.execute('CREATE INDEX IF NOT EXISTS word_forms_lemma_index ON word_forms (lemma)')
cur.execute('CREATE INDEX IF NOT EXISTS word_forms_type_index ON word_forms (type)')
cur.execute('CREATE INDEX IF NOT EXISTS word_forms_language_index ON word_forms (language)')
conn.commit()

# Download the file yourself!
context = etree.iterparse('enwiktionary-20240120-pages-articles.xml', tag='{http://www.mediawiki.org/xml/export-0.10/}page')

forms_list = []
words_list = []
lemmas_list = []
known_types = open('known_types.txt', 'r', encoding='utf-8').read().split('\n') # known and handled templates that may yield possible exceptions
o = open('forms.txt', 'w', encoding='utf-8') # write newly discovered templates with possible exceptions to this file
with open('lock', 'r', encoding='utf-8') as lockfile:
  lock = lockfile.read().strip()
lock_idx = int(lock)
cnt = 0
lval = ''
possible_exception_types = set(known_types)
for action, elem in context:
  title = elem.findtext('{http://www.mediawiki.org/xml/export-0.10/}title')
  ns = elem.findtext('{http://www.mediawiki.org/xml/export-0.10/}ns')
  if ns != '0': continue
  cnt += 1
  if cnt <= lock_idx: continue
  if cnt % 5000 == 0:
    print(f"{cnt} {title}")
    cur.executemany('INSERT OR IGNORE INTO word_forms (form, lemma, type, language) VALUES (?, ?, ?, ?)', forms_list)
    cur.executemany('INSERT OR IGNORE INTO words (word, language) VALUES (?, ?)', words_list)
    cur.executemany('INSERT OR IGNORE INTO lemmas (lemma, language) VALUES (?, ?)', lemmas_list)
    forms_list = []
    words_list = []
    lemmas_list = []
    lock_idx = cnt
    with open('lock', 'w', encoding='utf-8') as lockfile:
      lockfile.write(str(lock_idx))
    conn.commit()
  text = elem.findtext('{http://www.mediawiki.org/xml/export-0.10/}revision/{http://www.mediawiki.org/xml/export-0.10/}text')
  parsed = wtp.parse(text)
  levels = ['',title,'','','']
  for section in parsed.sections:
    if section.title == None: continue
    if section.level == 2:
      words_list.append((title, section.title))
    if section.level <= 4:
      levels[section.level] = section.title
      for i in range(section.level+1,5):
        levels[i] = ''
    for template in section.templates:
      string = template.string.strip()
      name = template.name.strip()
      if name.endswith(' of'):
        lang = levels[2]
        form_type = name
        lemma_pos = 0
        if "compound of" in name: continue
        if name in ["native or resident of"]: continue
        if len(template.arguments) == 0: continue

        # Usually templates named "something of" has the lemma in the second argument
        # And those named "(lang)-something of" has the lemma in the first argument
        # But there are lots of exceptions
        if name == "obsolete spelling of": lemma_pos = 2
        elif name == "hanja form of": lemma_pos = 1
        elif name == "Judeo-Arabic spelling of": lemma_pos = 1
        elif name == "Judeo-Urdu spelling of": lemma_pos = 1
        elif name == "sino-vietnamese spelling of": lemma_pos = 1
        elif name == "pi-nr-inflection of": lemma_pos = 2
        elif name == "sw-adj form of": lemma_pos = 2
        elif name == "ar-verbal noun of": lemma_pos = 2
        elif name == "t-prothesis of": lemma_pos = 2
        elif name in ["zh-erhua form of", "cmn-erhua form of"]:
          continue # TODO: handle these
        elif name.endswith("pronadv of"):
          continue # TODO: handle these
        elif name in ["ca-form of", "ka-form of"]:
          lemma_pos = 2
          form_type = template.arguments[0].value.strip()
        elif name == "sce-verb form of": lemma_pos = 2
        elif name == "cmn-pinyin of": lemma_pos = 1 # TODO: handle pinyin entries with more than one hanzi
        elif name == "he-infinitive of": lemma_pos = 2
        elif name in ["jv-krama inggil of", "jv-krama of"]: lemma_pos = 2
        # exceptions to here
        elif name == "form of": 
          lemma_pos = 3
          form_type = template.arguments[1].value.strip()
        elif len(template.arguments) == 1: lemma_pos = 1
        elif re.match('[a-z]{2,3}-', name) == None: # "something of" template
          lemma_pos = 2
        else: # "(lang)-something of" template
          lemma_pos = 1
        lemma = None
        for argument in template.arguments:
          if argument.name == str(lemma_pos):
            lemma = argument.value.strip()
        # look for possible exceptions
        if lemma == None or (len(template.arguments) > 1 and re.match('^[a-z]{2,3}$', lemma) != None):
          # no lemma or possible language code as lemma
          if name not in possible_exception_types:
            print(lemma)
            possible_exception_types.add(name)
            print(template)
            o.write(str(template))
            o.write('\n')
            o.flush()
        if '[[' in lemma:
          # remove links
          # replace [[(.+?)\|?(.+?)\]\] with \1
          lemma = re.sub(r'\[\[(.+?)\|?(.+?)\]\]', r'\1', lemma)
        if lemma.startswith('t=') or lemma.startswith('gloss='):
          pass # TODO: handle these
        lemma = lemma.replace('<', '').replace('>', '') # remove < and > from lemma
        lemmas_list.append((lemma, lang))
        forms_list.append((title, lemma, form_type, lang))

print(f"{cnt} {title}")
cur.executemany('INSERT OR IGNORE INTO word_forms (form, lemma, type, language) VALUES (?, ?, ?, ?)', forms_list)
cur.executemany('INSERT OR IGNORE INTO words (word, language) VALUES (?, ?)', words_list)
cur.executemany('INSERT OR IGNORE INTO lemmas (lemma, language) VALUES (?, ?)', lemmas_list)
lock_idx = cnt
with open('lock', 'w', encoding='utf-8') as lockfile:
  lockfile.write(str(lock_idx))
conn.commit()
conn.close()