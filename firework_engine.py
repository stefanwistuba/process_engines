import argparse
import json
import uuid
from fireworks import Firework, Workflow, FWorker, LaunchPad, ScriptTask
from fireworks.core.rocket_launcher import rapidfire
from flow_parser import FlowParser


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


class FireworkEngine:
    def __init__(self, output_path, input_file_path, db_connection):
        self.state = WorkFlowStatus(output_path)
        flow_parser = FlowParser(input_file_path)
        self.commands = flow_parser.parse_command()
        self.db = db_connection

    def execute(self, name):
        try:
            self.state.saveState('READY')
            lp = LaunchPad(**self.db)
            lp.reset('', require_password=False)
            tasks = []
            for idx, command in enumerate(self.commands):
                if idx > 0:
                    tasks.append(Firework(ScriptTask.from_str(
                        command), name=f'task_{idx}', fw_id=idx, parents=[tasks[idx-1]]))
                else:
                    tasks.append(Firework(ScriptTask.from_str(
                        command), name=f'task_{idx}', fw_id=idx))

            self.state.saveState('RUNNING')
            wf = Workflow(tasks, name=name)
            lp.add_wf(wf)
            rapidfire(lp)
            self.state.saveState('FINISHED')
        except Exception as e:
            print(e)
            self.state.saveState('ERROR')


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', metavar='Execution Path', required=True)
parser.add_argument('-wf', metavar='Workflow Path',
                    required=False, default=None)
parser.add_argument('-s', metavar='Status', required=False, default=None)

parser.add_argument('-dbhost', metavar='DB Host', required=False, default=None)
parser.add_argument('-dbport', metavar='DB Port',
                    type=int, required=False, default=None)
parser.add_argument('-dbname', metavar='DB Name', required=False, default=None)
parser.add_argument('-dbusername', metavar='DB Username',
                    required=False, default=None)
parser.add_argument('-dbpassword', metavar='DB Password',
                    required=False, default=None)
args = parser.parse_args()


if __name__ == '__main__':
    db_connection = {
        "host": args.dbhost,
        "port": args.dbport,
        "name": args.dbname,
        "username": args.dbusername,
        "password": args.dbpassword
    }

    # Execute Workflow / startCommand
    if args.wf != None:
        fp = FireworkEngine(args.p, args.wf, db_connection)
        fp.execute(uuid.uuid4())
    # Execute statusCommand
    elif args.s != None:
        ws = WorkFlowStatus(args.p)
        print(ws.getState())
