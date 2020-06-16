import argparse
import json


class FlowParser:
    def __init__(self, input_file_path):
        with open(input_file_path) as json_file:
            self.json_data = json.load(json_file)

        self.connections = self.json_data['connections']
        self.nodes = self.json_data['nodes']

    def transform_nodes(self):
        # Remove position key from nodes, as it is not relevant for the workflow
        result_nodes = []
        for node in self.nodes:
            node.pop('position', None)
            if node['model']['name'] != 'String' and node['model']['name'] != 'Boolean':
                result_nodes.append(node)
                
        self.nodes = result_nodes
    
        result_connections = []
        for connection in self.connections:
            in_id = list(filter(lambda node : node['id'] == connection['in_id'], self.nodes))
            out_id = list(filter(lambda node : node['id'] == connection['out_id'], self.nodes))

            if len(in_id) > 0 and len(out_id) > 0:
                result_connections.append(connection)
        self.connections = result_connections


        for node in self.nodes:
            node['num_inputs'] = len(list(filter(lambda connection : node['id'] == connection['in_id'], self.connections)))
        
        self.nodes = sorted(self.nodes, key=lambda node : node['num_inputs'])

        sorted_nodes = [self.nodes[0]]

        while len(sorted_nodes) < len(self.nodes):
            node = sorted_nodes[-1]
            out_connections = list(filter(lambda connection : node['id'] == connection['out_id'], self.connections))
            sorted_nodes.append(next(node for node in self.nodes if node['id'] == out_connections[0]['in_id']))

        self.nodes = sorted_nodes
        

    def parse_command(self):
        self.transform_nodes()
        for node in self.nodes:
            if node['model']['name'] == 'FileInput':
                node['command'] = f'cat {node["model"]["path"]} | '
                node['connect_next'] = True
            
            elif node['model']['name'] == 'FileOutput':
                node['command'] = f' > {node["model"]["outputFilePath"]}'
                node['connect_prev'] = True
            
            elif node['model']['name']  == 'ToolNode':
                first_command = node['model']['tool']['path']
                ports = node['model']['tool']['ports']
                arguments = [{'key': port['name'], 'value': port['value']} for port in ports if port['value'] != None and port['value']]
            
                node['command'] = f'{first_command}'
                for arg in arguments: 
                    if type(arg['value']) is bool:
                        arg['value'] = ''
                    if 'arg' in arg['key']:
                        node['command'] += f'{arg["value"]} '
                    else:
                        node['command'] += f'--{arg["key"]} {arg["value"]} '

        commands = []
        skip = False
        for idx, node in enumerate(self.nodes):
            if skip == True:
                skip = False
                continue
            if node.get('connect_next'):
                commands.append(node['command'] + self.nodes[idx + 1]['command'])
                skip = True
            elif node.get('connect_prev'):
                commands[-1] = commands[-1] + node['command']
            else:
                commands.append(node['command'])
        return commands