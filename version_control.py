# git_integration.py
from git import Repo
import os
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GitIntegration:
    def __init__(self, repo_path: str = 'code_docs'):
        self.repo_path = repo_path
        self.initialize_repo()
    
    def initialize_repo(self):
        """Initialize a new git repository if it doesn't exist"""
        try:
            if not os.path.exists(self.repo_path):
                os.makedirs(self.repo_path)
                self.repo = Repo.init(self.repo_path)
                logger.info(f"Initialized new git repository at {self.repo_path}")
            else:
                self.repo = Repo(self.repo_path)
        except Exception as e:
            logger.error(f"Error initializing git repo: {str(e)}")
            raise
    
    def save_documentation(self, username: str, filename: str, content: str) -> str:
        """Save documentation to git repository"""
        try:
            file_path = os.path.join(self.repo_path, f"{filename}.md")
            with open(file_path, 'w') as f:
                f.write(content)
            
            # Stage and commit the file
            self.repo.index.add([file_path])
            self.repo.index.commit(f"Documentation update by {username} at {datetime.now()}")
            
            return file_path
        except Exception as e:
            logger.error(f"Error saving to git: {str(e)}")
            raise
    
    def get_history(self, filename: str) -> List[Dict]:
        """Get commit history for a specific file"""
        try:
            file_path = os.path.join(self.repo_path, f"{filename}.md")
            commits = []
            for commit in self.repo.iter_commits(paths=file_path):
                commits.append({
                    'hash': commit.hexsha,
                    'author': commit.author.name,
                    'date': commit.committed_datetime,
                    'message': commit.message
                })
            return commits
        except Exception as e:
            logger.error(f"Error getting git history: {str(e)}")
            return []
    
    def get_version(self, filename: str, commit_hash: str) -> str:
        """Get specific version of a file"""
        try:
            file_path = os.path.join(self.repo_path, f"{filename}.md")
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error getting version: {str(e)}")
            return ""