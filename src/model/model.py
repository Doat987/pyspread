#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2008 Martin Manns
# Distributed under the terms of the GNU General Public License
# generated by wxGlade 0.6 on Mon Mar 17 23:22:49 2008

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

Model
=====

The model contains the core data structures of pyspread.
It is divided into layers.

Layer 3: 
Layer 2: 
Layer 1: 
Layer 0: 

"""

import itertools
from types import SliceType

import wx

from lib.irange import slice_range

from config import MAX_UNREDO

class KeyValueStore(dict):
    """Key-Value store in memory. Currently a dict with default value None.
    
    This class represents layer 0 of the model.
    
    """
    
    def __missing__(self, value):
        """Returns the default value None"""
        
        return
        
# End of class KeyValueStore

# ------------------------------------------------------------------------------

class CellAttributes(list):
    """Stores cell formatting attributes in a list of 2 - tuples
    
    The first element of each tuple is a Selection.
    The second element is a dict of attributes that are altered.
    
    The class provides attribute read access to single cells via __getitem__
    Otherwise it behaves similar to a list.
    
    """
    
    def __getitem__(self, key):
        """Returns attribute dict for a single key"""
        
        assert not any(type(key_ele) is SliceType for key_ele in key)
        
        result_dict = {}
        
        for selection, attr_dict in self:
            if key in selection:
                result_dict.update(attr_dict)
        
        return result_dict

# End of class CellAttributes


class DictGrid(KeyValueStore):
    """The core data class with all information that is stored in a pys file.
    
    Besides grid code access via standard dict operations, it provides 
    the following attributes:
    
    * cell_attributes: Stores cell formatting attributes
    * macros:          String of all macros
    
    This class represents layer 1 of the model.
    
    Parameters
    ----------
    shape: n-tuple of integer
    \tShape of the grid
    
    """
    
    def __init__(self, shape):
        KeyValueStore.__init__(self)
        
        self.shape = shape
        
        self.cell_attributes = CellAttributes()
        self.macros = u""
    
    def __getitem__(self, key):
        
        shape = self.shape
        
        for axis, key_ele in enumerate(key):
            if shape[axis] <= key_ele or key_ele < -shape[axis]:
                raise IndexError, "Grid index" + \
                      str(key) + "outside grid shape" + str(shape)
        
        return KeyValueStore.__getitem__(key)

# End of class DictGrid

# ------------------------------------------------------------------------------


class UnRedo(object):
    """Undo/Redo framework class.
    
    For each undo-able operation, the undo/redo framework stores the
    undo operation and the redo operation. For each step, a 4-tuple of:
    1) the function object that has to be called for the undo operation
    2) the undo function parameters as a list
    3) the function object that has to be called for the redo operation
    4) the redo function parameters as a list
    is stored.
    
    One undo step in the application can comprise of multiple operations.
    Undo steps are separated by the string "MARK".
    
    The attributes should only be written to by the class methods.

    Attributes
    ----------
    undolist: List
    \t
    redolist: List
    \t
    active: Boolean
    \tTrue while an undo or a redo step is executed.

    """
    
    def __init__(self):
        """[(undofunc, [undoparams, ...], redofunc, [redoparams, ...]), 
        ..., "MARK", ...]
        "MARK" separartes undo/redo steps
        
        """
        
        self.undolist = []
        self.redolist = []
        self.active = False
        
    def mark(self):
        """Inserts a mark in undolist and empties redolist"""
        
        if self.undolist != [] and self.undolist[-1] != "MARK":
            self.undolist.append("MARK")
    
    def undo(self):
        """Undos operations until next mark and stores them in the redolist"""
        
        self.active = True
        
        while self.undolist != [] and self.undolist[-1] == "MARK":
            self.undolist.pop()
            
        if self.redolist != [] and self.redolist[-1] != "MARK":
            self.redolist.append("MARK")
        
        while self.undolist != []:
            step = self.undolist.pop()
            if step == "MARK": 
                break
            self.redolist.append(step)
            step[0](*step[1])
        
        self.active = False
        
    def redo(self):
        """Redos operations until next mark and stores them in the undolist"""
        
        self.active = True
        
        while self.redolist and self.redolist[-1] == "MARK":
            self.redolist.pop()
        
        if self.undolist:
            self.undolist.append("MARK")
        
        while self.redolist:
            step = self.redolist.pop()
            if step == "MARK": 
                break
            self.undolist.append(step)
            step[2](*step[3])
            
        self.active = False

    def reset(self):
        """Empties both undolist and redolist"""
        
        self.__init__()

    def append(self, undo_operation, operation):
        """Stores an operation and its undo operation in the undolist
        
        undo_operation: (undo_function, [undo_function_attribute_1, ...])
        operation: (redo_function, [redo_function_attribute_1, ...])
        
        """
        
        # If the lists grow too large they are emptied
        if len(self.undolist) > MAX_UNREDO or \
           len(self.redolist) > MAX_UNREDO:
            self.reset()
        
        # Check attribute types
        for unredo_operation in [undo_operation, operation]:
            iter(unredo_operation)
            assert len(unredo_operation) == 2
            assert hasattr(unredo_operation[0], "__call__")
            iter(unredo_operation[1])
        
        if not self.active:
            self.undolist.append(undo_operation + operation)

# End of class UnRedo


class DataArray(object):
    """DataArray provides enhanced grid read/write access.
    
    Enhancements comprise:
     * Slicing
     * Multi-dimensional operations such as insertion and deletion along 1 axis
     * Undo/redo operations
    
    This class represents layer 2 of the model.
    
    Parameters
    ----------
    shape: n-tuple of integer
    \tShape of the grid
    
    """
    
    def __init__(self, shape):
        self.dict_grid = DictGrid(shape)
    
    # Shape mask
    
    def _get_shape(self):
        """Returns dict_grid shape"""
        
        return self.dict_grid.shape
        
    def _set_shape(self, shape):
        """Deletes all cells beyond new shape and sets dict_grid shape"""
        
        # Delete each cell that is beyond new borders
        
        old_shape = self.shape
        
        if any(new_axis < old_axis 
               for new_axis, old_axis in zip(shape, old_shape)):
            for key in self.dict_grid:
                if any(key_ele >= new_axis 
                       for key_ele, new_axis in zip(key, shape)):
                    self.dict_grid.pop(key)
        
        # Set dict_grid shape attribute
        
        self.dict_grid.shape = shape

    
    shape = property(_get_shape, _set_shape)

    # Pickle support
    
    def __getstate__(self):
        """Returns dict_grid for pickling
        
        Note that all persistent data is contained in the DictGrid class
        
        """
        
        return {"dict_grid": self.dict_grid}
    
    # Slice support
    
    def _is_slice_like(self, obj):
        """Returns True if obj is slice like, i.e. has attribute indices"""
        
        return hasattr(obj, "split")
        
    def _is_string_like(self, obj):
        """Returns True if obj is string like, i.e. has method split"""
        
        return hasattr(obj, "indices")
    
    def __getitem__(self, key):
        """Adds slicing access to cell code retrieval
        
        The cells are returned as a generator of generators, of ... of unicode.
        
        Parameters
        ----------
        key: n-tuple of integer or slice
        \tKeys of the cell code that is returned
        
        Note
        ----
        Classical Excel type addressing (A$1, ...) may be added here
        
        """
        
        for key_ele in key:
            if self._is_slice_like(key_ele):
                # We have something slice-like here 
                
                return self.cell_array_generator(key)
                
            elif self._is_string_like(key_ele):
                # We have something string-like here 
                
                raise NotImplementedError
                
        # key_ele should be a single cell
        
        return self.dict_grid[key]
    
    
    def __setitem__(self, key, value):
        """Accepts index and slice keys"""
        
        single_keys_per_dim = []
        
        for axis, key_ele in enumerate(key):
            if self._is_slice_like(key_ele):
                # We have something slice-like here 
                
                single_keys_per_dim.append(slice_range(key_ele, 
                                                       length = key[axis]))
                
            elif self._is_string_like(key_ele):
                # We have something string-like here 
                
                raise NotImplementedError
            
            else:
                # key_ele should be a single cell
                
                single_keys_per_dim.append(key_ele)
        
        single_keys = itertools.product(single_keys_per_dim)
        
        for single_key in single_keys:
            self.dict_grid[single_key] = value
    
    def cell_array_generator(self, key):
        """Generator traversing cells specified in key
        
        Parameters
        ----------
        key: Iterable of Integer or slice
        \tThe key specifies the cell keys of the generator
        
        """
        
        for i, key_ele in enumerate(key):
            
            # Get first element of key that is a slice
            
            if type(key_ele) is SliceType:
                slc_keys = slice_range(key_ele, self.dict_grid.shape[i])
                
                key_list = list(key)
                
                key_list[i] = None
                
                has_subslice = any(type(ele) is SliceType for ele in key_list)
                                            
                for slc_key in slc_keys:
                    key_list[i] = slc_key
                    
                    if has_subslice:
                        # If there is a slice left yield generator
                        yield self.cell_array_generator(key_list)
                        
                    else:
                        # No slices? Yield value
                        yield self[tuple(key_list)]
                    
                break
    
    def insert(self, insertion_point, no_to_insert, axis):
        """Inserts no_to_insert rows/cols/tabs/... before insertion_point
        
        Axis specifies number of dimension, i.e. 0 == row, 1 == col, ...
        
        """
        
        if not 0 <= axis <= len(self.shape):
            raise ValueError, "Axis not in grid dimensions"
        
        if insertion_point > self.shape[axis] or \
           insertion_point <= -self.shape[axis]:
            raise IndexError, "Insertion point not in grid"
        
        deleted_cells = {} # For undo
        new_cells = {}
        
        for key in self:
            if key[axis] >= insertion_point:
                new_key = list(key)
                new_key[axis] += no_to_insert
                
                new_cells[tuple(new_key)] = \
                deleted_cells[key] = \
                    self.dict_grid.pop(key)
        
        self.dict_grid.update(new_cells)

    def delete(self, deletion_point, no_to_delete, axis):
        """Deletes no_to_delete rows/cols/tabs/... starting with deletion_point
        
        Axis specifies number of dimension, i.e. 0 == row, 1 == col, ...
        
        """
        
        if no_to_delete < 0:
            raise ValueError, "Cannot delete negative number of rows/cols/..."
        
        if not 0 <= axis <= len(self.shape):
            raise ValueError, "Axis not in grid dimensions"
        
        if deletion_point > self.shape[axis] or \
           deletion_point <= -self.shape[axis]:
            raise IndexError, "Deletion point not in grid"
        
        deleted_cells = {} # For undo
        new_cells = {}
        
        for key in self:
            if deletion_point <= key[axis] < deletion_point + no_to_delete:
                deleted_cells[key] = self.dict_grid.pop(key)
            
            elif key[axis] >= deletion_point + no_to_delete:
                new_key = list(key)
                new_key[axis] -= no_to_delete
                
                new_cells[tuple(new_key)] = \
                deleted_cells[key] = \
                    self.dict_grid.pop(key)
        
        self.dict_grid.update(new_cells)

# End of class DataArray

# ------------------------------------------------------------------------------

class CodeArray(DataArray):
    """CodeArray provides objects when accessing cells via __getitem__
    
    Cell code can be accessed via function call
    
    This class represents layer 3 of the model.
    
    """
    
    operators = ["+", "-", "*", "**", "/", "//",
             "%", "<<", ">>", "&", "|", "^", "~",
             "<", ">", "<=", ">=", "==", "!=", "<>",
            ]
    
    __call__ = DataArray.__getitem__
    
    def __getitem__(self, key):
        """Yields to other events and returns _eval_cell
       
        This allows GUI to unlock on deep iterations through the grid
        
        """
        
        wx.Yield()

        return self._eval_cell(key)
    
    def _eval_cell(self, key):
        """Evaluates one cell"""
        
        # Set up environment for evaluation
        env = globals().copy()
        env.update( {'X':key[0], 'Y':key[1], 'Z':key[2],
                     'R':key[0], 'C':key[1], 'T':key[2],
                     'S':self } )
        
        # Check if there is a global assignment
        split_exp = self.dict_grid[key].split("=")
        
        # Assignment is valid iif 
        #  * only one term in front of "=" and 
        #  * no "==" and 
        #  * no operators left and 
        #  * parentheses balanced
        
        has_assignment = \
            len(split_exp) > 1 and \
            len(split_exp[0].split()) == 1 and \
            split_exp[1] != "" and \
            (not max(op in split_exp[0] for op in self.operators)) and \
            split_exp[0].count("(") == split_exp[0].count(")")
        
        # If only 1 term in front of the "=" --> global
        
        if has_assignment:
            glob_var = split_exp[0].strip()
            expression = "=".join(split_exp[1:])
        else:
            glob_var = None
            expression = self.dict_grid[key]
        
        try:
            result = eval(expression, env, {})
        except Exception, err:
            result = err
        
        if glob_var is not None:
            globals().update({glob_var: result})
        
        return result
    
# End of class CodeArray

