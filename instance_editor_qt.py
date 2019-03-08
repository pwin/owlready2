# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2013-2019 Jean-Baptiste LAMY
# LIMICS (Laboratoire d'informatique médicale et d'ingénierie des connaissances en santé), UMR_S 1142
# University Paris 13, Sorbonne paris-Cité, Bobigny, France

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import owlready2, owlready2.editor
from owlready2 import *
from owlready2.instance_editor import *

import editobj3, editobj3.undoredo as undoredo, editobj3.introsp as introsp, editobj3.field as field, editobj3.editor as editor, editobj3.editor_qt as editor_qt

import PyQt5.QtCore    as qtcore
import PyQt5.QtWidgets as qtwidgets
import PyQt5.QtGui     as qtgui


class QtOntologyInstanceEditor(OntologyInstanceEditor, editor_qt.QtEditorTabbedDialog):    
  def check_save(self):
    if self.undo_stack.undoables != self.last_undoables:
      box = qtwidgets.QMessageBox()
      box.setText(editobj3.TRANSLATOR(u"Save modifications before closing?"))
      box.setStandardButtons(qtwidgets.QMessageBox.Save | qtwidgets.QMessageBox.Discard | qtwidgets.QMessageBox.Cancel)
      box.setDefaultButton(qtwidgets.QMessageBox.Cancel)
      response = box.exec()
      
      if   response == qtwidgets.QMessageBox.Discard: return 0
      if   response == qtwidgets.QMessageBox.Cancel:  return 1
      elif response == qtwidgets.QMessageBox.Save:
        self.on_save()
        return self.check_save() # The user may have canceled a "save as" dialog box !
      
    else: return 0
    
  def prompt_save_filename(self):
    filename = qtwidgets.QFileDialog.getSaveFileName(self.window, editobj3.TRANSLATOR(u"Save as..."), os.path.join(onto_path[0], self.ontology.name), "OWL/XML (*.owl)")[0]
    return filename
    
  



