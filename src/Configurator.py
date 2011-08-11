#!/usr/bin/env python
#
# coding: utf8
#

import gtk
import re

import sys
import os.path

class ConfigFile:
    
    def __init__(self, filename):
        
        self.filename = filename
        
        self.title = os.path.basename(filename)
        self.file = open(filename, "r")
        
        self.config = {
            "comment": "//",
            "define": "`define",
            "command": "//="
        }
        
        self.lines = []
        
        current_tab = "Main"
        self.tabs = {current_tab: []}
        self.tabs_titles = [current_tab]
        
        re0 = re.compile("//\s(\w.+)")
        re1 = re.compile("\/\/=(valid)\s(.+)")
        re2 = re.compile("(\/\/)?`define\s+(\w+)((\s+([\w'\.]+))|(\s+\/\/\s*(.*)))?\s+")
        
        current_title = ""
        current_valid = ""
        current_select = None
        current_ifdef = 0
        
        for n, row in enumerate(self.file):
            
            self.lines.append(row)
            
            if re.match("\s+", row):
                current_title = ""
                current_valid = ""
                continue
            
            if re.match("\/\/=select", row):
                current_select = ConfigOptionSelect(
                    title = current_title
                )
                continue
            
            if re.match("\/\/=end", row):
                self.tabs[current_tab].append(current_select)
                current_select = None
                continue
            
            if re.match("\s*`ifn?def.*", row):
                current_ifdef += 1
            
            if re.match("\s*`endif.*", row):
                current_ifdef -= 1
            
            if current_ifdef > 0:
                continue
            
            m = re.match("\/\/=tab ([\w ]+)\s+", row)
            
            if m:
                current_tab = m.group(1)
                if current_tab not in self.tabs_titles:
                    self.tabs[current_tab] = []
                    self.tabs_titles.append(current_tab)
                continue
            
            m = re0.match(row)
            
            if m:
                current_title = m.group(1)
                continue
            
            m = re1.match(row)
            
            if m:
                current_valid = m.group(2)
                continue
            
            m = re2.match(row)
            
            if m:
                (current_select if (current_select is not None) else self.tabs[current_tab]).append(ConfigOption(
                    line = n,
                    name = m.group(2),
                    title = ((m.group(7) if (m.group(7) is not None) else m.group(2)) if (current_select is not None) else (current_title if len(current_title) > 0 else m.group(2))),
                    valid = current_valid,
                    checkbox = (m.group(4) is None),
                    default = (m.group(5) if (m.group(5) is not None) else (m.group(1) is None))
                ))
                current_title = ""
                current_valid = ""
                continue
            
        
        self.file.close()
        
    
    def save(self):
        
        for tab in self.tabs:
            for opt in self.tabs[tab]:
                opt.save(self)
        
        self.file = open(self.filename, "w")
        
        for line in self.lines:
            self.file.write(line.rstrip(" \n\r") + "\n")
        
        self.file.close()
        
    

class ConfigOption(gtk.HBox):
    
    def __init__(self, **kwargs):
        
        gtk.HBox.__init__(self, True)
        
        self.options = kwargs
        
        if kwargs['checkbox']:
            self.entry = gtk.CheckButton()
            self.entry.set_active(kwargs['default'])
        else:
            self.entry = gtk.Entry()
            self.entry.set_text(kwargs['default'])
        
        self.pack_start(gtk.Label(kwargs['title']))
        self.pack_start(self.entry)
        
    
    def save(self, cfgfile, comment = ""):
        
        s = ""
        
        if self.options['checkbox']:
            s += "" if self.entry.get_active() else "//"
        
        s += "`define "
        s += self.options['name']
        
        if not self.options['checkbox']:
            s += " "
            s += self.entry.get_text()
        
        if len(comment) > 0:
            s += " // " + comment
        
        cfgfile.lines[self.options['line']] = s
        
    

class ConfigOptionSelect(gtk.HBox):
    
    def __init__(self, **kwargs):
        
        gtk.HBox.__init__(self, True)
        
        self.opts = []
        self.options = kwargs
        
        self.entry = gtk.combo_box_new_text()
        
        self.pack_start(gtk.Label(kwargs['title']))
        self.pack_start(self.entry)
        
        self.entry.connect("changed", self.onchanged)
        
    
    def append(self, opt):
        
        self.opts.append(opt)
        self.entry.append_text(opt.options['title'])
        
        if opt.options['default']:
            self.entry.set_active(len(self.opts) - 1)
        
    
    def onchanged(self, *args):
        
        for i, opt in enumerate(self.opts):
            opt.entry.set_active(i == self.entry.get_active())
        
    
    def save(self, cfgfile):
        
        for opt in self.opts:
            opt.save(cfgfile, opt.options['title'])
        
    

class ConfigWindow(gtk.Window):
    
    def __init__(self, cfgfilename = None):
        
        gtk.Window.__init__(self)
        
        self.set_title("Configurator")
        self.set_default_size(400, 600)
        
        self.box = gtk.VBox()
        self.button = gtk.Button("Save")
        self.notebook = gtk.Notebook()
        
        self.add(self.box)
        
        self.box.pack_start(self.notebook, True)
        self.box.pack_start(self.button, False)
        
        self.button.connect('clicked', lambda b: self.save())
        
        if cfgfilename is not None:
            self.load(ConfigFile(cfgfilename))
        
    
    def load(self, cfg):
        
        self.set_title(cfg.title + " - Configurator")
        
        self.configfile = cfg
        
        for tab in cfg.tabs_titles:
            box = gtk.VBox()
            for opt in cfg.tabs[tab]:
                box.pack_start(opt, False)
            box.pack_start(gtk.Label(""), True)
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
            sw.add_with_viewport(box)
            self.notebook.append_page(sw, gtk.Label(tab))
        
        self.show_all()
        
    
    def save(self):
        
        self.configfile.save()
        
    
    def run(self):
        
        def ondel(win, *args):
            gtk.main_quit()
            win.hide()
            return True
        
        handler_id = self.connect("delete_event", ondel)
        
        gtk.main()
        
        self.disconnect(handler_id)
        
    

if __name__ == '__main__':
    ConfigWindow(sys.argv[1]).run()
