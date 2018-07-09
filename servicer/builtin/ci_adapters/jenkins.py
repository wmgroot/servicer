from .base_ci_adapter import BaseCIAdapter

class CIAdapter(BaseCIAdapter):

    def __init__(self):
        super().__init__()

        # https://wiki.jenkins.io/display/JENKINS/Building+a+software+project
        self.env_map['BRANCH_NAME'] = 'BRANCH'
        self.env_map['BUILD_DISPLAY_NAME'] = 'BUILD_NAME'
        self.env_map['BUILD_ID'] = 'BUILDID'
        self.env_map['BUILD_NUMBER'] = 'BUILD_NUMBER'
        self.env_map['BUILD_TAG'] = 'TAG'
        self.env_map['BUILD_URL'] = 'BUILD_URL'
        self.env_map['CHANGE_AUTHOR'] = 'PR_USERNAME'
        self.env_map['CHANGE_AUTHOR_DISPLAY_NAME'] = 'PR_AUTHOR_NAME'
        self.env_map['CHANGE_AUTHOR_EMAIL'] = 'PR_AUTHOR_EMAIL'
        self.env_map['CHANGE_ID'] = 'PR_NUMBER'
        self.env_map['CHANGE_TARGET'] = 'PR_TARGET'
        self.env_map['CHANGE_TITLE'] = 'PR_TITLE'
        self.env_map['CHANGE_URL'] = 'PR_URL'
        self.env_map['EXECUTOR_NUMBER'] = 'NODE_INDEX'
        self.env_map['GIT_BRANCH'] = 'BRANCH'
        self.env_map['GIT_COMMIT'] = 'COMMIT'
        self.env_map['GIT_URL'] = 'REPO_URL'
        self.env_map['JENKINS_HOME'] = 'HOME'
        self.env_map['JENKINS_URL'] = 'CI_URL'
        self.env_map['JOB_BASE_NAME'] = 'JOB_BASE_NAME'
        self.env_map['JOB_NAME'] = 'JOB_NAME'
        self.env_map['JOB_URL'] = 'JOB_URL'
        self.env_map['NODE_LABELS'] = 'NODE_LABELS'
        self.env_map['NODE_NAME'] = 'NODE_NAME'
        self.env_map['WORKSPACE'] = 'WORKING_DIRECTORY'
