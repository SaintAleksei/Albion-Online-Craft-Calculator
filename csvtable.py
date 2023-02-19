#!/usr/bin/python3

import csv
import numpy as np

class CSVTable:
  def __init__(self, columns=None, rows=None):
    if columns is None:
      columns = []
    if rows is None:
      rows = []
    self._col_names = columns
    self._row_names= rows 
    self._data = np.ndarray((len(self._row_names), len(self._col_names)), dtype=np.float64)

  def read(self, csv_file):
    with open(csv_file, 'r') as file_csv:
      reader = csv.reader(file_csv, delimiter=',')
      try:
        self._col_names = [v for v in reader.__next__()][1:]
      except StopIteration:
        return

      self._row_names = []
      self._data = []
      for row in reader:
        row = [v for v in row]
        self._row_names.append(row[0])
        self._data.append(row[1:])

      self._data = np.array(self._data)

  def write(self, csv_file):
    with open(csv_file, 'w') as file_csv:
      writer = csv.writer(file_csv, delimiter=',')
      writer.writerow([None] + self._col_names)
      for name, row in zip(self._row_names, self._data):
        writer.writerow([name] + row.tolist())
    
  def get_column(self, name):
    ret = {}
    try:
      idx = self._col_names.index(name)
      ret = {k: v for k, v in zip(self._row_names, self._data[:, idx])}
    except:
      pass
    return ret

  def get_row(self, name):
    ret = {}
    try:
      idx = self._row_names.index(name)
      ret = {k: v for k, v in zip(self._col_names, self._data[idx])}
    except:
      pass
    return ret

  def add_column(self, name, column):
    self._col_names.append(name)
    new_column = np.array([v for v in column.values()])
    self._data = np.column_stack((self._data, new_column))
    
  def add_row(self, name, row):
    self._row_names.append(name)
    new_row = np.array([v for v in row.values()])
    self._data = np.row_stack((self._data, new_row))

  def rows(self):
    return self._row_names.copy()

  def columns(self):
    return self._col_names.copy()

  def __getitem__(self, row, col):
    row_idx = self._row_names.index(row)
    col_idx = self._col_names.index(col)
    return self._data[row, col] 

  def __setitem__(self, row, col, val):
    row_idx = self._row_names.index(row)
    col_idx = self._col_names.index(col)
    self._data[row, col] = val

def simple_test():
  tb = CSVTable()
  tb.read('test.csv')

  print(tb.get_column('col1'))
  print(tb.get_row('row2'))
  tb.add_column('col5', {'row1': 1, 'row2': 2, 'row3': 3})
  tb.add_row('row4', {'col1': 1, 'col2': 2, 'col3': 3, 'col4': 4, 'col5': 5})
  
  tb.write('test_new.csv')

if __name__ == '__main__':
  simple_test()
