import argparse
import json
import yaml
import os

from flow_parser import FlowParser
        
"""
    Class containing all the logic required to parse *.flow-Files into
    a corresponding representation of the Common Workflow Language (CWL)
    Specification.
    Currently the CWL Specification version used in this project is v1.0
"""
class FlowToCWLParser:
    """
        Makes use of the FlowParser class with slight changes at certain steps
        to fit the CWL definition and workflow
    """
    def __init__(self, flow_file_path):
        fp = FlowParser(flow_file_path)
        fp.transform_nodes()
        self.nodes = fp.nodes
        self.connections = fp.connections

        self.steps = []
        self.workflow_input_list = []
        self.workflow_job_values = []
        self.workflow_output_list = []
    
    """
        Function to construct the parameter input file (*.yml) required for the
        CWL. Transforms the data into a corresponding dictionary for later parsing into 
        the yaml-file.
    """
    def constructCWLInput(self, name, type, input_position, shortName=None, current_step=None):
        cwl_input = {}
        # Used to differentiate between different params with the same name
        constructed_name = f'{current_step}_{name}'
        cwl_input[constructed_name] = {}
        if type == 'flag':
            cwl_input[constructed_name]['type'] = 'boolean'
        else:
            cwl_input[constructed_name]['type'] = type

        cwl_input[constructed_name]['inputBinding'] = {'position': input_position}
        if 'arg' not in name:
            if shortName != None:
                cwl_input[constructed_name]['inputBinding'] = {**cwl_input[constructed_name]['inputBinding'], 'prefix': f'-{shortName}'}
            else:
                cwl_input[constructed_name]['inputBinding'] = {**cwl_input[constructed_name]['inputBinding'], 'prefix': f'-{name}'}
        return cwl_input

    """
        Parsing the required information to create the *.yml-Parameter File as well
        as the job information files for each step (CommandLineTool class) and the
        overarching Workflow class file (both *.cwl) containing each step and their 
        inputs / outputs
    """
    def parse_commands(self):
        prev_node_stdout = None
        for node in self.nodes:
            # Currently we only consider FileInput, FileOutput and ToolNode
            if node['model']['name'] == 'FileInput':
                self.steps.append('cat')
                self.workflow_input_list.append([
                    { 'cat_path': { 'type': 'File', 'inputBinding': { 'position': 0}}}
                    ])

                input_file_path = node["model"]["path"]
                if '~' in input_file_path:
                    input_file_path = os.path.expanduser(input_file_path)

                self.workflow_job_values.append([{ 'cat_path': {'class': 'File', 'path': input_file_path }}])
                self.workflow_output_list.append([{ 'name': 'cat_stdout', 'type': 'stdout' }])
                # Set Flag for next node to know it will receive stdin
                prev_node_stdout = {'node_id': node['id'], 'name': 'cat_stdout'}
            
            elif node['model']['name'] == 'FileOutput':
                fileoutput_inputs = []
                if prev_node_stdout != None:
                    for cnn in self.connections:
                        if cnn['out_id'] == prev_node_stdout['node_id'] and cnn['out_index'] == 1 and cnn['in_id'] == node['id']:
                            fileoutput_inputs.append({
                                prev_node_stdout['name']: {'type': 'stdin'}
                            })
                    prev_node_stdout = None

                self.steps.append('print')
                fileoutput_inputs.append(
                    { 'print_outputFilePath': { 'type': 'File', 'inputBinding': { 'position': 0}}}
                    )
                self.workflow_input_list.append(fileoutput_inputs)

                output_file_path = node["model"]["outputFilePath"]
                if '~' in output_file_path:
                    output_file_path = os.path.expanduser(output_file_path)

                self.workflow_job_values.append([{ 'print_outputFilePath': {'class': 'File', 'path': output_file_path }}])
                self.workflow_output_list.append([])
                
            elif node['model']['name'] == 'ToolNode':
                input_cwl_list = []
                input_job_values = []

                if prev_node_stdout != None:
                    for cnn in self.connections:
                        if cnn['out_id'] == prev_node_stdout['node_id'] and cnn['in_id'] == node['id'] and cnn['in_index'] == 4:
                            input_cwl_list.append({
                                prev_node_stdout['name']: {'type': 'stdin'}
                            })
                    prev_node_stdout = None

                # Extract shell command
                step_name = node['model']['tool']['path'].strip()
                self.steps.append(step_name)
                # Extract all port values from the ports of the ToolNode
                ports = node['model']['tool']['ports']
                arguments = [
                    {
                        'key': port['name'], 'value': port['value'],
                        'type': port['type'], 'position': port['position'],
                        'shortName': port['shortName']
                    } for port in ports if port['value'] != None and port['value']
                ]
                # Check if the ToolNode's stdout has a connection to another input
                output_appended = False
                for port in ports:
                    if port['name'] == 'stdout':
                        stdout_index = port['port_index']
                        for cnn in self.connections:
                            if cnn['out_id'] == node['id'] and cnn['out_index'] == stdout_index:
                                self.workflow_output_list.append([{ 'name': f'{step_name}_stdout',  'type': 'stdout' }])
                                output_appended = True
                                prev_node_stdout = {'node_id': node['id'], 'name': f'{step_name}_stdout'}
                if not output_appended:
                    self.workflow_output_list.append(None)

                for arg in arguments:                    
                    # Check if the value contains a dot, an indication for a file
                    # Required as CWL needs to use the 'File' type for actual files
                    # Using a string for the path of the file does not seem to work
                    if isinstance(arg['value'], str) and '.' in arg['value']:
                        cwl_input = self.constructCWLInput(
                            name=arg['key'], type='File', 
                            input_position=arg['position'], shortName=arg['shortName'],
                            current_step=step_name)

                        input_cwl_list.append(cwl_input)

                        correct_file_path = arg['value']
                        # Tilde cant be correctly parsed to user by the cwl-tool
                        if '~' in correct_file_path:
                            correct_file_path = os.path.expanduser(correct_file_path)
                        input_job_values.append({f'{step_name}_{arg["key"]}': {'class': 'File', 'path': correct_file_path}})

                    else:
                        cwl_input = self.constructCWLInput(
                            name=arg['key'], type=arg['type'], 
                            input_position=arg['position'], shortName=arg['shortName'], 
                            current_step=step_name)

                        input_cwl_list.append(cwl_input)
                        input_job_values.append({f'{step_name}_{arg["key"]}': arg['value']})
                self.workflow_input_list.append(input_cwl_list)
                self.workflow_job_values.append(input_job_values)
    
    """
        Function to create all the yml files required to
        execute a CWL Workflow runner, based on the CWL v1.0 standard
        3 types of file are required for our purposes:
            1. CWL Files for each processing step, containing 
                the command to be executed an required parameters
            2. A single parameter file containing all 
                the parameter required to run the processes
            3. An overarching Workflow file, containing 
                all the steps to be executed in sequential orders and their required parameters
    """
    def create_workflow_files(self):
        self.parse_commands()
        # Standard opener for cwl command files
        cwl_opener = ['#!/usr/bin/env cwl-runner\n\n',
                          'cwlVersion: v1.1\n']

        # 1. Create cwl files for each step in the workflow
        dependent_inputs = []
        for idx, step in enumerate(self.steps):
            cwl_file_name = f'{step}.cwl'
            cwl_basecommand = f'baseCommand: [{step}]\n'
            cwl_stdout = ''
            if step == 'print':
                cwl_basecommand = f'baseCommand: [xargs, echo]\n'

            if self.workflow_output_list[idx] != None:
                for out in self.workflow_output_list[idx]:
                    if out['type'] == 'stdout':
                        cwl_stdout = f'stdout: {step}_output.txt\n'

            cwl_inputs = {'inputs': self.workflow_input_list[idx] }
            for step_input in cwl_inputs['inputs']:
                key = list(step_input.keys())[0]
                key_origin = key.split('_')[0]
                if step_input[key]['type'] == 'stdin':
                    dependent_inputs.append({'name': f'{key_origin}/{key}', 'belongsTo': step, 'param': key})
            formatted_outputs = []

            if self.workflow_output_list[idx] != None:
                for elem in self.workflow_output_list[idx]:
                    formatted_outputs.append({ elem['name']: { 'type': elem['type']}})
            cwl_outputs = {'outputs': formatted_outputs }

            with open(cwl_file_name, 'w') as output:
                output.writelines(cwl_opener)
                output.write('class: CommandLineTool\n')
                output.write(cwl_basecommand)
                output.write(cwl_stdout)

                stream_input = yaml.dump(cwl_inputs, default_flow_style=False)
                stream_output = yaml.dump(cwl_outputs, default_flow_style=False)
                # Remove leading scores, but keep the ones for the prefix
                output.write(stream_input.replace('- ', '  '))
                output.write(stream_output.replace('- ', '  '))

        wf_name = '-'.join(self.steps)
        wf_steps= {}
        wf_steps['steps'] = []

        flattened_job_values = []
        for sublist in self.workflow_job_values:
            for item in sublist:
                flattened_job_values.append(item)

        # 2. Create param inputs file
        workflow_param_name = f'{wf_name}-params.yml'
        with open(workflow_param_name, 'w') as output:
                stream = yaml.dump(flattened_job_values, default_flow_style=False)
                stream = stream.replace('- ', '')
                stream = stream.replace('\'\'\'', '\'')
                output.write(stream)
        
        wf_inputs = []
        input_keys = []
        output_keys = []
        for idx, lst in enumerate(self.workflow_input_list):
            for param in lst:
                current_param_key = list(param.keys())[0]
                if not param[current_param_key]['type'] == 'stdin':
                    input_keys.append(current_param_key)
                    wf_inputs.append({ f'{current_param_key}': param[current_param_key]['type']})
                else:
                    output_keys.append(current_param_key)
        for idx, step in enumerate(self.steps):
            new_step = {}

            relevant_params = [{param: param} for param in input_keys if f'{step}_' in param]

            for d_input in dependent_inputs:
                if d_input['belongsTo'] == step:
                    relevant_params.append({ d_input['param']: d_input['name']})

            output_params = [param for param in output_keys if f'{step}_' in param]
            new_step[step] = {
                'run': f'{step}.cwl',
                'in': relevant_params,
                'out': f'{output_params}'
            }
            wf_steps['steps'].append(new_step)

        # 3. Create overarching workflow.cwl
        worflow_file_name = f'{wf_name}-workflow.cwl'
        with open(worflow_file_name, 'w') as output:
            output.writelines(cwl_opener)
            output.write('class: Workflow\n')
            
            wf_params_stream = yaml.dump({'inputs': wf_inputs }, default_flow_style=False)
            wf_params_stream = wf_params_stream.replace('-', ' ')
            output.write(wf_params_stream)

            output.write('outputs: []\n')

            wf_step_stream = yaml.dump(wf_steps, default_flow_style=False)
            wf_step_stream = wf_step_stream.replace('-', ' ')
            wf_step_stream = wf_step_stream.replace("\'", '')
            output.write(wf_step_stream)
        
        return (worflow_file_name, workflow_param_name)
