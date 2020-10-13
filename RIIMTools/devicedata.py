"""Helper tools to get device-specific information.

  TODO: Implement additional functions to access individual properties,
  showing qubit connectivity, etc.
"""
import pandas as pd
from qiskit import IBMQ, providers
account = IBMQ.load_account()

def get_device_props(backend_name):
  """Get device properties.

  Device properties are retrieved for each qubit, and U2 and cx gates. The
  properties are written to a csv file. Valid devices are given in list_devices.

  The output csv/DataFrame is laid out in a dictionary format:

    Keys: Qubit, T1 [us], T2 [us], Frequency [GHz], Readout error, \
          Single-qubit U2 error date, CNOT error rate

  Each of the keys has a one-to-one map key-to-value, with the exception of
  'CNOT error rate'. The 'CNOT error rate' key value is a list of maps from each
  (control) qubit to its CNOT-connected (target) qubits via dictionaries, e.g.

    print(out_dict_props_gates['CNOT error rate'][1])

  prints the list of qubit 1 CNOT connections.

  Args:
    backend_name (str): Name of the backend to query.

  Returns:
    Dictionary containing device calibration data.

  Raises:
    QiskitBackendNotFoundError: If backend is not valid.
  """
  provider = IBMQ.get_provider(group='open')
  ibmq_backends_avail = provider.backends()[2:]
  list_backends_avail_names = [be.name() for be in ibmq_backends_avail]
  if backend_name not in list_backends_avail_names:
    raise providers.exceptions.QiskitBackendNotFoundError(
      '\'backend_name\' must be one of: ', \
        ', '.join(list_backends_avail_names))

  the_backend = provider.get_backend(backend_name)
  # Pull IBMQ device properties
  full_properties = the_backend.properties()
  props_dict = the_backend.properties().to_dict()
  last_update_date = full_properties.last_update_date
  # Dictionary for access to qubit properties of interest (map from Qiskit)
  dict_props_device_qubit = {0: 'T1 [us]', 1: 'T2 [us]', 2: 'Frequency [GHz]', \
    4: 'Readout error'}

  # Qubit properties from device
  props_qubits = props_dict['qubits']
  # Qubit dictionary of properties for output
  dict_props_qubit = {'Qubit': [], 'T1 [us]': [], 'T2 [us]': [], \
    'Frequency [GHz]': [], 'Readout error': []}
  dict_update_date = {'Last update date': []}
  # Loop over the number of qubits
  for q in range(0, len(props_qubits)):
    # The current qubit
    this_qubit = props_qubits[q]
    # Current qubit name
    this_qubit_name = 'Q' + str(q)
    # Add the qubit name to the 'Qubit' column of output
    dict_props_qubit['Qubit'].append(this_qubit_name)
    # Add the last update date
    dict_update_date['Last update date'].append(last_update_date)
    # Loop over the properties of interest
    for i in dict_props_device_qubit:
      # Property name (key)
      prop_name = dict_props_device_qubit[i]
      # Value of the property
      prop_value =  this_qubit[i]['value']
      # Add property value to the corresponding key of output
      dict_props_qubit[prop_name].append(prop_value)

  # Gate properties
  props_gates = props_dict['gates']
  # Gate dictionary of properties for output
  dict_props_gates = {'Single-qubit U2 error rate': [], \
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
  dict_props_gates['Single-qubit U2 error rate'] = list_u2_gates
  dict_props_gates['CNOT error rate'] = list_cx_gates

  # Combine qubit and gate dicts
  output_data = {**dict_props_qubit, **dict_props_gates, **dict_update_date}

  return output_data


def write_device_props_csv(dict_data, output_csv_name=None):
  """Write device (qubit and gate) data to a csv file.

  The dictionary contains keys:
    Qubit, T1 [us], T2 [us], Frequency [GHz], Readout error,
    Single-qubit U2 error rate, CNOT error rate, Last update date

  that are used as the csv column headers.

  Args:
    dict_data (dictionary): Dictionary of data, adhering to the format given in
               get_device_props, to write to file.
    output_csv_name (str): Name of output file.

  Returns:
    Device properties in a DataFrame object.
  """
  # List of headings for csv output
  out_csv_headings = ['Qubit', 'T1 [us]', 'T2 [us]', 'Frequency [GHz]', \
    'Readout error', 'Single-qubit U2 error rate', 'CNOT error rate', \
    'Last update date']

  # Create a DataFrame
  df = pd.DataFrame(dict_data, columns = out_csv_headings)

  # Format output name and write csv
  if output_csv_name is None:
    output_csv_name = 'device_properties.dat'
  df.to_csv(output_csv_name, index = False, header = True)

  return df


def get_cx_connected_qubits(df, ctl):
  """Retrieves the target qubits from the given control qubit.

  Given a control qubit, a list of connected (control) qubits is returned based
  on the device data in the provided DataFrame.

  Args:
    df (DataFrame): Device properties.
    ctl: Control qubit to return connected (target) qubits from.
  
  Returns:
    List of connected (target) qubits.
  """
  # List of qubits to return
  connected_qubits = []
  # Get the cx column data
  cx_data = df['CNOT error rate'][ctl]
  # Loop over list of dictionaries
  for d in cx_data:
    # Get the key
    for key, _ in d.items():
      # Parse key to get connected qubit. Assume key of the form 'cxCTL_TGT'
      connected_qubits.append('Q' + key.split('_')[1])

  return connected_qubits


def get_cx_error_rate(df, ctl, tgt):
  """ Gets the cx/CNOT error rate between two qubits.

  Given a control (ctl) and target (tgt) qubit, the error rate of the cx/CNOT
  gate connecting them is retrieved from a DataFrame with device properties.
  Note that the cx/CNOT is not necessarily symmetric; the error rate between
  q1 (ctl) and q2 (tgt) is not in general the same as q2 (ctl) and q1 (tgt), so
  this method needs to be called for each pair (ctl, tgt).

  Args:
    ctl: Index of the control qubit.
    tgt: Index of the target qubit.

  Returns:
    Error rate of the cx/CNOT gate connecting ctl and tgt.

  Raises:
    Exception if ctl and tgt are the same qubit index, or ctl and tgt are not
    cx/CNOT-connected.
  """
  # Sanity check: ensure ctl and tgt are distinct
  if ctl == tgt:
    raise Exception('ctl and tgt must be distinct qubits.')
  tgt_name = 'Q' + str(tgt)
  # Sanity check: ensure ctl and tgt are connected via cx/CNOT
  if tgt_name not in get_cx_connected_qubits(df, 1):
    raise Exception('ctl and tgt are not connected via a cx/CNOT gate.')
  # Construct gate name from ctl and tgt
  gate_name = 'cx' + str(ctl) + '_' + str(tgt)
  # Get relevant row and column from DataFrame
  cx_data = df['CNOT error rate'][ctl]
  # Get the error rate. N.B. this is not efficient.
  for d in cx_data:
    if gate_name in d.keys():
      return d[gate_name]
