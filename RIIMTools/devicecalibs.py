"""Helper tools to get device-specific information.
"""
import pandas as pd
import numpy as np
from qiskit import IBMQ
account = IBMQ.load_account()

# List of valid devices (as of 2020-10-13)
list_devices = ['ibmq_essex','ibmq_london','ibmq_ourense',\
  'ibmq_rome', 'ibmq_valencia']
# List of headings for csv output
out_csv_headings = ['Qubit', 'T1 [us]', 'T2 [us]', 'Frequency [GHz]', \
  'Readout error', 'Single-qubit U2 error rate', 'CNOT error rate']
# Dictionary for access to qubit properties of interest (map from Qiskit)
dict_props_qubit = {0: 'T1 [us]', 1: 'T2 [us]', 2: 'Frequency [GHz]', \
  4: 'Readout error'}


def get_device_props(device_name):
  """Get device properties.

  Device properties are retrieved as per out_csv_headings. The properties are
  written to a csv file. Valid devices are given in list_devices.

  Args:
    device_name (str): Name of the device to query.
  """
  provider = IBMQ.get_provider(group='open')
  device = provider.get_backend(device_name)

  # Pull IBMQ device properties
  full_properties = device.properties()
  props_dict = device.properties().to_dict()

  # Qubit properties from device
  props_qubits = props_dict['qubits']
  # Qubit dictionary of properties for output
  out_dict_props_qubits = {'Qubit': [], 'T1 [us]': [], 'T2 [us]': [], \
    'Frequency [GHz]': [], 'Readout error': []}
  # Loop over the number of qubits
  for q in range(0, len(props_qubits)):
    # The current qubit
    this_qubit = props_qubits[q]
    # Current qubit name
    this_qubit_name = 'Q' + str(q)
    # Add the qubit name to the 'Qubit' column of output
    out_dict_props_qubits['Qubit'].append(this_qubit_name)
    # Loop over the properties of interest
    for i in dict_props_qubit:
      # Property name (key)
      prop_name = dict_props_qubit[i]
      # Value of the property
      prop_value =  this_qubit[i]['value']
      # Add property value to the corresponding key of output
      out_dict_props_qubits[prop_name].append(prop_value)

  # Gate properties
  props_gates = props_dict['gates']
  # Gate dictionary of properties for output
  out_dict_props_gates = {'Single-qubit U2 error rate': [], \
    'CNOT error rate': []}
  # List of U2 gates
  list_u2_gates = []
  # List of cx/CNOT gates; a list of list (one for each qubit) of dictionaries
  list_cx_gates = []
  # Loop over all gates
  for g in range(0, len(props_gates)):
    # Name of the current gate, e.g. cx0_1, u2_0, etc.
    this_gate_name = props_gates[g]['name']
    # Current gate parameters
    params = props_gates[g]['parameters']
    # Get the value of current gate's error
    gate_error_value = params[0]['value']
    # Check if we have a U2/Hadamard gate
    if this_gate_name.find('u2') == 0:
      # Append to U2 list
      list_u2_gates.append(gate_error_value)
    # Check if we have a cx/CNOT gate
    elif this_gate_name.find('cx') == 0:
      # The control bit of this cx gate
      ctl = props_gates[g]['qubits'][0]
      # Instantiate a dictionary of the form {gate_name: error_vale}
      dict_this_gate = {this_gate_name: gate_error_value}
      # Check if we already have a list of dicts for ctl
      if (ctl + 1) > len(list_cx_gates):
        # No: add a new list for ctl
        list_cx_gates.append([dict_this_gate])
      # We have a list for ctl
      else:
        # Add dict to ctl for tgt
        list_cx_gates[ctl].append(dict_this_gate)
  
  # Assign output dict to the lists constructed above
  out_dict_props_gates['Single-qubit U2 error rate'] = list_u2_gates
  out_dict_props_gates['CNOT error rate'] = list_cx_gates

  # Combine qubit and gate dicts
  output_data = {**out_dict_props_qubits, **out_dict_props_gates}

  # Create a DataFrame
  df = pd.DataFrame(output_data, columns = out_csv_headings)
  # Write to csv: get date and format output name
  import datetime
  timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
  date = full_properties.last_update_date.strftime('%Y%m%d')
  # str_date = str(date) + '.' + timezone
  csv_name = device_name + '.' + str(date) + '.devcalib'
  df.to_csv(csv_name, index = False, header = True)
  return df
