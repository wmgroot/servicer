import json
import os

from .topological_order import toposort2

class DependencyGrapher():
    def __init__(self, config, active_services, steps, step_order, active_steps, logger=None):
        self.toposort2 = toposort2
        self.logger = logger
        self.config = config
        self.active_services = active_services
        self.steps = steps
        self.step_order = step_order
        self.active_steps = active_steps

    def order_service_steps(self, services):
        follow_dependencies = True
        if self.config['args']['ignore_dependencies']:
            follow_dependencies = False

        dependencies = {}

        for service_name in services:
            service = self.config['services'][service_name]

            for step_name in self.active_steps:
                if step_name in service['steps']:
                    service_step_name = '%s:%s' % (service_name, step_name)
                    self.add_dependencies(dependencies, service_step_name, follow_dependencies)

        self.add_wildcard_dependencies(dependencies, follow_dependencies)

        # remove orphaned build dependencies
        if self.config['args']['ignore_dependencies']:
            dep_keys = dependencies.keys()
            for key, value in dependencies.items():
                dependencies[key] = set([v for v in value if v in dep_keys])

        self.logger.log('Dependency Graph:')
        self.logger.log(json.dumps(dependencies, indent=4, sort_keys=True, default=str))
        return self.toposort2(dependencies)

    def service_step_depends_on(self, service_step_name):
        name_pieces = service_step_name.split(':')
        service_name = name_pieces[0]
        service = self.config['services'][service_name]
        step_name = name_pieces[1]

        depends_on = []

        # service level user-defined custom dependencies
        depends_on.extend(self.get_depends_on(service))

        # step level user-defined custom dependencies
        depends_on.extend(self.get_depends_on(service['steps'][step_name]))

        # default step based dependencies
        if self.config['graph']['implicit-step-dependencies'] and step_name in self.step_order:
            step_index = self.step_order.index(step_name)
            while step_index > 0:
                step_index -= 1
                dep_step_name = self.step_order[step_index]

                if dep_step_name in service['steps']:
                    depends_on.append('%s:%s' % (service_name, dep_step_name))
                    break

        # append implied step dependencies
        depends_on = self.fill_implied_step_dependencies(depends_on, step_name)

        return depends_on

    def fill_implied_step_dependencies(self, depends_on, step_name):
        deps = []
        for d in depends_on:
            if ':' in d:
                deps.append(d)
            elif 'steps' in self.config['services'][d] and step_name in self.config['services'][d]['steps']:
                deps.append('%s:%s' % (d, step_name))
        return deps

    def get_depends_on(self, config):
        depends_on = []
        if 'depends_on' in config:
            if isinstance(config['depends_on'], list):
                depends_on.extend(config['depends_on'])
            else:
                depends_on.append(config['depends_on'])
        return depends_on

    def add_dependencies(self, dependencies, service_step_name, follow_dependencies=True):
        if service_step_name in dependencies:
            return  # only calculate dependencies for each service-step once
        else:
            dependencies[service_step_name] = set()

        depends_on = self.service_step_depends_on(service_step_name)

        service_step_name_pieces = service_step_name

        for dep in depends_on:
            dep_pieces = dep.split(':')
            service_dependency = dep_pieces[0]
            step_dependency = dep_pieces[1]

            if service_dependency == '*':
                # self.delayed_dependencies.append(service_step_name)
                self.add_dependency(dependencies, service_step_name, service_dependency, step_dependency, False)
                continue
            elif service_dependency not in self.config['services']:
                msg = 'Invalid service dependency specified: %s, "%s" must be included in services: [%s]' % (dep, service_dependency, ','.join(self.config['services'].keys()))
                raise ValueError(msg)

            if step_dependency in self.steps:
                self.add_dependency(dependencies, service_step_name, service_dependency, step_dependency, follow_dependencies)
            else:
                msg = 'Invalid step dependency specified: %s, "%s" must be included in steps: [%s]' % (dep, step_dependency, ','.join(self.steps.keys()))
                raise ValueError(msg)

    def add_dependency(self, dependencies, service_step_name, service_name, step_name, follow_dependencies):
        dep_service_step_name = '%s:%s' % (service_name, step_name)
        dependencies[service_step_name].add(dep_service_step_name)
        if follow_dependencies:
            self.add_dependencies(dependencies, dep_service_step_name, follow_dependencies)

    def add_wildcard_dependencies(self, dependencies, follow_dependencies=True):
        dependency_list = list(dependencies)
        for service_step_name in reversed(dependency_list):
            depends_on = dependencies[service_step_name].copy()
            for dep in depends_on:
                if dep.startswith('*'):
                    dependencies[service_step_name].remove(dep)
                    hard_dependency = False

                    if dep.endswith('!'):
                        dep = dep[0:-1]
                        hard_dependency = True

                    step_dependency = dep.split(':')[1]

                    all_services = []
                    if hard_dependency:
                        all_services = self.config['services'].keys()
                    else:
                        service_names = [d.split(':')[0] for d in dependencies.keys()]
                        all_services = list(set(service_names))

                    for _service_name in all_services:
                        if step_dependency in self.config['services'][_service_name]['steps']:
                            self.add_dependency(dependencies, service_step_name, _service_name, step_dependency, follow_dependencies)
