from .base_ci_adapter import BaseCIAdapter

class CIAdapter(BaseCIAdapter):

    def __init__(self, logger=None):
        super().__init__(logger=logger)

        # https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        self.env_map['CI_COMMIT_REF_NAME'] = 'BRANCH'
        self.env_map['CI_JOB_ID'] = 'BUILD_NUMBER'
        self.env_map['CI_JOB_URL'] = 'BUILD_URL'
        self.env_map['CI_JOB_NAME'] = 'JOB_NAME'
        self.env_map['CI_PROJECT_URL'] = 'REPO_URL'
        self.env_map['CI_COMMIT_SHA'] = 'COMMIT'
        self.env_map['CI_COMMIT_TAG'] = 'TAG'
        self.env_map['GITLAB_USER_LOGIN'] = 'USERNAME'
        self.env_map['CI_PROJECT_DIR'] = 'WORKING_DIRECTORY'
