import subprocess

def run(command, check=True, shell=True, hide_output=False):
    print('executing: %s' % command)
    result = { 'command': command }

    try:
        command_result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=check,
            shell=shell,
        )
        # command_result = subprocess.run(command, check = check, shell = shell)
        result['command_result'] = command_result
        result['stdout'] = command_result.stdout.decode('utf-8')
        result['status'] = command_result.returncode

        if not hide_output:
            print(result['stdout'])

    except subprocess.CalledProcessError as e:
        print('failed: %s' % e.returncode)
        print(e.output.decode('utf-8'))
        raise

    return result
