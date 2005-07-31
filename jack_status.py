### jack_status: module which holds the ripping and encoding status for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2002  Arne Zellentin <zarne@users.sf.net>

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; either version 2 of the License, or
### (at your option) any later version.

### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.

### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import string

from jack_globals import NUM, cf
import jack_term
import jack_ripstuff

enc_status = {}     # status messages are stored here
enc_cache = {}      # sometimes status messages are stored here
dae_status = {}     # status messages are stored here

def init(todo):
    global enc_status, enc_cache, dae_status
    for i in todo:
        dae_status[i[NUM]] = ""
        enc_status[i[NUM]] = ""
        enc_cache[i[NUM]] = ""

def extract(status):
    for i in status.keys():
        if status[i]['dae']:
            dae_status[i] = status[i]['dae']
        if status[i]['enc']:
            enc_status[i] = status[i]['enc']

def enc_stat_upd(num, string):
    global enc_status
    enc_status[num] = string
    jack_term.tmod.enc_stat_upd(num, string)

def dae_stat_upd(num, string):
    global enc_status
    dae_status[num] = string
    jack_term.tmod.dae_stat_upd(num, string)

def print_status(form = 'normal'):
    for i in jack_ripstuff.all_tracks_todo_sorted:
        if form != 'normal' or not jack_ripstuff.printable_names:
            print cf['_name'] % i[NUM] + ":", dae_status[i[NUM]], enc_status[i[NUM]]
        else:
            print jack_ripstuff.printable_names[i[NUM]] + ":", dae_status[i[NUM]], enc_status[i[NUM]]

def get_2_line(buf, default="A failure occured"):
    tmp = string.split(buf, "\n")
    if len(tmp) >= 2:
        return string.strip(tmp[-2])
    else:
        return default

