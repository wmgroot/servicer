from .base_ci_adapter import BaseCIAdapter

class CIAdapter(BaseCIAdapter):

    def __init__(self, logger=None):
        super().__init__(logger=logger)

        # https://circleci.com/docs/2.0/env-vars/#built-in-environment-variables
        self.env_map['CIRCLE_BRANCH'] = 'BRANCH'
        self.env_map['CIRCLE_BUILD_NUM'] = 'BUILD_NUMBER'
        self.env_map['CIRCLE_BUILD_URL'] = 'BUILD_URL'
        self.env_map['CIRCLE_COMPARE_URL'] = 'DIFF_URL'
        self.env_map['CIRCLE_INTERNAL_TASK_DATA'] = 'RESULT_DATA'
        self.env_map['CIRCLE_JOB'] = 'JOB_NAME'
        self.env_map['CIRCLE_NODE_INDEX'] = 'NODE_INDEX'
        self.env_map['CIRCLE_NODE_TOTAL'] = 'NODE_TOTAL'
        self.env_map['CIRCLE_PR_NUMBER'] = 'PR_NUMBER'
        self.env_map['CIRCLE_PR_REPONAME'] = 'PR_REPO_NAME'
        self.env_map['CIRCLE_PR_USERNAME'] = 'PR_USERNAME'
        self.env_map['CIRCLE_PREVIOUS_BUILD_NUM'] = 'PREVIOUS_BUILD_NUMBER'
        self.env_map['CIRCLE_PROJECT_REPONAME'] = 'REPO_NAME'
        self.env_map['CIRCLE_PROJECT_USERNAME'] = 'CI_PROJECT_NAME'
        self.env_map['CIRCLE_PULL_REQUEST'] = 'PR_URL'
        self.env_map['CIRCLE_PULL_REQUESTS'] = 'PR_URLS'
        self.env_map['CIRCLE_REPOSITORY_URL'] = 'REPO_URL'
        self.env_map['CIRCLE_SHA1'] = 'COMMIT'
        self.env_map['CIRCLE_TAG'] = 'TAG'
        self.env_map['CIRCLE_USERNAME'] = 'USERNAME'
        self.env_map['CIRCLE_WORKFLOW_ID'] = 'WORKFLOW_ID'
        self.env_map['CIRCLE_WORKING_DIRECTORY'] = 'WORKING_DIRECTORY'
