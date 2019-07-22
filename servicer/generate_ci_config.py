import sys
from .topological_order import toposort2

def generate_ci_config(config=None, path=None):
    if not config:
        print('You must provide a valid deploy config!')

    create_ci_steps(config)
    output_configs = config['ci']['output_configs']
    generators = [getattr(sys.modules[__name__], 'generate_%s' % oc['provider']) for oc in output_configs]
    results = [g(config, path) for g in generators]

def create_ci_steps(config):
    steps = []

    if 'commands' in config['ci']:
        steps.append(create_step(
            name='ci_setup',
            commands=config['ci']['commands'],
        ))

    build_and_test_steps = []
    for service in config['services'].values():
        print(service)
        commands = []
        for step in ('build', 'test'):
            if 'steps' in service and step in service['steps'] and 'commands' in service['steps'][step]:
                commands.extend(service['steps'][step]['commands'])
            elif service.get('module') and hasattr(service['module'], step):
                commands.append('python %s/deploy.py --step %s --service %s' % (config['path'], step, service['name']))
        if len(commands) > 0:
            build_and_test_steps.append(create_step(
                name='%s_build_and_test' % service['name'],
                commands=commands,
                docker=service.get('docker')
            ))

    if len(build_and_test_steps) > 0:
        steps.append(create_step(
            name='build_and_test',
            type='parallel',
            steps=build_and_test_steps,
        ))

    deploy_dependencies = parse_dependencies(config['services'])
    deploy_order = toposort2(deploy_dependencies)

    for parallel_step in deploy_order:
        deploy_steps = []
        for deploy_step in parallel_step:
            deploy_steps.append(create_step(
                name='%s_deploy' % deploy_step,
                commands=['python %s/deploy.py --step deploy --service %s' % (config['path'], deploy_step)],
                docker=config['services'][deploy_step].get('docker')
            ))

        steps.append(create_step(
            name='deploy_%s' % '_'.join(parallel_step),
            type='parallel',
            steps=deploy_steps,
        ))

    config['ci']['steps'] = steps
    return steps

def create_step(**args):
    step = {
        'name': args['name'],
        'type': args.get('type') or 'step',
    }
    for arg in ('commands', 'docker', 'steps'):
        if arg in args:
            step[arg] = args[arg]

    return step

def parse_dependencies(services):
    dependencies = {}

    for service in services.values():
        deploy_deps = service.get('depends_on', [])
        if not isinstance(deploy_deps, list):
            deploy_deps = [deploy_deps]

        dependencies[service['name']] = set(deploy_deps)

    return dependencies

def generate_bitbucket(config, path):
    bitbucket_config = {
        'image': config['ci']['image'],
        'pipelines': { 'default': [] },
    }

    generate_bitbucket_pipeline(config['ci']['steps'], bitbucket_config['pipelines']['default'])

    if path:
        write_yaml(bitbucket_config, '%s/bitbucket-pipelines.yml' % path)
    else:
        import json
        print(json.dumps(bitbucket_config, indent=2))

def generate_bitbucket_pipeline(steps, pipeline=[]):
    for ci_step in steps:
        step = {}

        if ci_step['type'] == 'parallel':
            step[ci_step['type']] = []
            generate_bitbucket_pipeline(ci_step['steps'], step[ci_step['type']])
        else:
            step[ci_step['type']] = {
                'script': ci_step['commands'],
            }
            if ci_step.get('docker'):
                step[ci_step['type']]['services'] = ['docker']

        pipeline.append(step)


def write_yaml(data, file_path):
    from ruamel import yaml

    with open(file_path, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    autogen_text = '# AUTOGENERATED FILE (build/deploy.py)\n# python build/deploy.py --generate-ci'
    with open(file_path, 'r') as original: data = original.read()
    with open(file_path, 'w') as modified: modified.write('%s\n\n%s\n%s' % (autogen_text, data, autogen_text))
