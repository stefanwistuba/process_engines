# Process Engines Prototypes

This is a collection of process engines prototypes based on an existing implementation of
the complete Workflow.

All Process Engines receive their instructions from the corresponding \*.flow-files, which are then parsed
into a format which can be turned into a corresponding Workflow using their own Process Engines.

Currently Prototypes for the Fireworks Process Engine and the Common Workflow Language (CWL) Specification
has been created

All examples have been implemented with Python v3.7

## Proccess Engine with FireWorks

This is a Process Engine using Fireworks.

It can be executed like this:

```sh
python firework_engine.py -p . -wf ./example_awk.flow

python firework_engine.py -p . -wf ./example_sort_cp.flow
```

Additional arguments are:

| Argument Name |     Default | Description                     |
| :------------ | ----------: | :------------------------------ |
| `dbhost`      | "localhost" | Hostname of the MongoDb server. |
| `dbport`      |       27017 | Port of the MongoDb server.     |
| `dbname`      | "fireworks" | Database name to use.           |
| `dbusername`  |        None | Username of the MongoDb server. |
| `dbpassword`  |        None | Password of the MongoDb server. |

After a task was executed the status can be checked with inside the run path:

```sh
python firework_engine.py -p . -s True
```

## Process Enginge based on the Common Workflow Language (CWL) Specification

This is a Process Engine based on the Common Workflow Language (CWL) Specification

For this project, we have made use of the following package:

```
pip install cwlref-runner
```

The Package contains the CWL-Implementation (cwltool) and a runner (cwl-runner) which can be used to execute
the Workflow. Alternatively, other runners should also be viable for use, as long as they comform to the
CWL - Specification, although this has not been tested yet.

### Information

The overall idea behind this implementation is a conversion of the _.flow-Files into a corresponding
representation of _.cwl- and \*.yml-Files, required for the excution of a Process Engine abiding the
CWL-Specification.

It can be executed like this:

```sh
python cwl_engine.py -p . -wf example_sort_cp.flow
python3 cwl_engine.py -p . -wf example_awk.flow
```

Additional arguments are:

| Argument Name |      Default | Description                                         |
| :------------ | -----------: | :-------------------------------------------------- |
| `-en`         | "cwl-runner" | CWL Implementation to be used as the Process Engine |

After a task was executed the status can be checked with inside the run path:

```sh
python cwl_engine.py -p . -s True
```
