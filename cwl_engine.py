import argparse
import json
import os
from flow_to_cwl_parser import FlowToCWLParser


class WorkFlowStatus:
    def __init__(self, path):
        self.file_path = f'{path}/.workflow-status.json'

    def saveState(self, state):
        with open(self.file_path, 'w') as out_file:
            json.dump({'state': state}, out_file)

        return True

    def getState(self):
        state = None
        with open(self.file_path) as json_file:
            state = json.load(json_file)
        return state['state']


class CWLEngine:
    def __init__(self, output_path, input_file_path, cwl_engine):
        self.state = WorkFlowStatus(output_path)
        self.cwl_parser = FlowToCWLParser(input_file_path)
        self.cwl_engine = cwl_engine

    def execute(self):
        wf_name, wf_param_name = self.cwl_parser.create_workflow_files()

        try:
            self.state.saveState('READY')
            self.state.saveState('RUNNING')
            os.system(f'{self.cwl_engine} {wf_name} {wf_param_name}')
            self.state.saveState('FINISHED')
        except Exception as e:
            print(e)
            self.state.saveState('ERROR')


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', metavar='Execution Path', required=True)
parser.add_argument('-wf', metavar='Workflow Path',
                    required=False, default=None)
parser.add_argument('-s', metavar='Status', required=False, default=None)
parser.add_argument('-en', metavar='CWL-Engine', required=False, default='cwl-runner')

args = parser.parse_args()


if __name__ == '__main__':
    # Execute Workflow / startCommand
    if args.wf != None:
        cwl = CWLEngine(args.p, args.wf, args.en)
        cwl.execute()
    # Execute statusCommand
    elif args.s != None:
        ws = WorkFlowStatus(args.p)
        print(ws.getState())

