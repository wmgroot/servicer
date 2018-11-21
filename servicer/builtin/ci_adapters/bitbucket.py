from .base_ci_adapter import BaseCIAdapter

class CIAdapter(BaseCIAdapter):

    def __init__(self, logger=None):
        super().__init__(logger=logger)

        # https://confluence.atlassian.com/bitbucket/environment-variables-794502608.html
        self.env_map['BITBUCKET_BUILD_NUMBER'] = 'BUILD_NUMBER'
        self.env_map['BITBUCKET_CLONE_DIR'] = 'CLONE_DIR'
        self.env_map['BITBUCKET_COMMIT'] = 'COMMIT'
        self.env_map['BITBUCKET_REPO_OWNER'] = 'REPO_OWNER'
        self.env_map['BITBUCKET_REPO_OWNER_UUID'] = 'REPO_OWNER_UUID'
        self.env_map['BITBUCKET_REPO_SLUG'] = 'REPO_SLUG'
        self.env_map['BITBUCKET_REPO_UUID'] = 'REPO_UUID'
        self.env_map['BITBUCKET_BRANCH'] = 'BRANCH'
        self.env_map['BITBUCKET_TAG'] = 'TAG'
        self.env_map['BITBUCKET_BOOKMARK'] = 'BOOKMARK'
        self.env_map['BITBUCKET_PARALLEL_STEP'] = 'PARALLEL_STEP'
        self.env_map['BITBUCKET_PARALLEL_STEP_COUNT'] = 'PARALLEL_STEP_COUNT'
