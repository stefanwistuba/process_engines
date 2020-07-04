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
            
            elif node['model']['name'] == 'FileOutput':
                self.steps.append('print')
                self.workflow_input_list.append([
                    { 'print_outputFilePath': { 'type': 'File', 'inputBinding': { 'position': 0}}}
                    ])

                output_file_path = node["model"]["outputFilePath"]
                if '~' in output_file_path:
                    output_file_path = os.path.expanduser(output_file_path)
                print(output_file_path)

                self.workflow_job_values.append([{ 'print_outputFilePath': {'class': 'File', 'path': output_file_path }}])
                
            elif node['model']['name'] == 'ToolNode':
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

                input_cwl_list = []
                input_job_values = []
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
                          'cwlVersion: v1.0\n']

        # 1. Create cwl files for each step in the workflow
        for idx, step in enumerate(self.steps):
            cwl_file_name = f'{step}.cwl'
            cwl_basecommand = f'baseCommand: [{step}]\n'
            if step == 'print':
                cwl_basecommand = f'baseCommand: [>]\n'
            cwl_inputs = {'inputs': self.workflow_input_list[idx] }
            cwl_outputs = {'outputs': [] }

            with open(cwl_file_name, 'w') as output:
                output.writelines(cwl_opener)
                output.write('class: CommandLineTool\n')
                output.write(cwl_basecommand)

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
                output.write(stream.replace('- ', ''))
        
        wf_inputs = []
        input_keys = []
        for idx, lst in enumerate(self.workflow_input_list):
            for param in lst:
                current_param_key = list(param.keys())[0]
                input_keys.append(current_param_key)
                wf_inputs.append({ f'{current_param_key}': param[current_param_key]['type']})
        
        for idx, step in enumerate(self.steps):
            new_step = {}

            relevant_params = [{param: param} for param in input_keys if f'{step}_' in param]
            new_step[step] = {
                'run': f'{step}.cwl',
                'in': relevant_params,
                'out': []
            }
            wf_steps['steps'].append(new_step)

        # 3. Create overarching workflow.cwl
        worflow_file_name = f'{wf_name}-workflow.cwl'
        with open(worflow_file_name, 'w') as output:
            output.writelines(cwl_opener)
            output.write('class: Workflow\n')

            wf_params_stream = yaml.dump({'inputs': wf_inputs }, default_flow_style=False)
            output.write(wf_params_stream.replace('-', ' '))

            output.write('outputs: []\n')

            wf_step_stream = yaml.dump(wf_steps, default_flow_style=False)
            output.write(wf_step_stream.replace('-', ' '))
        
        return (worflow_file_name, workflow_param_name)
