import os
from git import Repo, GitCommandError, InvalidGitRepositoryError
from git.exc import NoSuchPathError
from datetime import datetime
import shutil
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitIntegrationError(Exception):
    """Custom exception for Git integration errors"""
    pass

class GitManager:
    def __init__(self, base_path: str = 'docs_repo', remote_url: Optional[str] = None):
        """
        Initialize GitManager with a base path and optional remote URL.
        
        Args:
            base_path (str): Local path for the git repository
            remote_url (str, optional): URL of remote repository
        """
        self.base_path = Path(base_path)
        self.remote_url = remote_url
        self.repo = self._initialize_repository()
        self.metadata_file = self.base_path / 'metadata.json'
        self._initialize_metadata()

    def _initialize_repository(self) -> Repo:
        """
        Initialize or load the git repository.
        
        Returns:
            Repo: Initialized git repository
        
        Raises:
            GitIntegrationError: If repository initialization fails
        """
        try:
            if not self.base_path.exists():
                self.base_path.mkdir(parents=True)
                repo = Repo.init(self.base_path)
                logger.info(f"Initialized new git repository at {self.base_path}")
                
                # Set up initial commit
                readme_path = self.base_path / 'README.md'
                readme_path.write_text("# Documentation Repository\nManaged by Documentation Generator\n")
                repo.index.add(['README.md'])
                repo.index.commit("Initial commit")
                
                # Configure git user if not set
                if not repo.config_reader().has_section('user'):
                    config_writer = repo.config_writer()
                    config_writer.set_value("user", "name", "Documentation Generator")
                    config_writer.set_value("user", "email", "doc.generator@example.com")
                    config_writer.release()
                
                # Set up remote if provided
                if self.remote_url:
                    repo.create_remote('origin', self.remote_url)
                
                return repo
            
            return Repo(self.base_path)
            
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            logger.error(f"Error initializing repository: {str(e)}")
            raise GitIntegrationError(f"Failed to initialize repository: {str(e)}")

    def _initialize_metadata(self):
        """Initialize metadata file for tracking document information"""
        if not self.metadata_file.exists():
            metadata = {
                'documents': {},
                'last_updated': datetime.now().isoformat()
            }
            self.metadata_file.write_text(json.dumps(metadata, indent=2))
            self.repo.index.add(['metadata.json'])
            self.repo.index.commit("Initialize metadata tracking")

    def _update_metadata(self, doc_id: str, info: Dict):
        """Update metadata for a specific document"""
        try:
            metadata = json.loads(self.metadata_file.read_text())
            metadata['documents'][doc_id] = {
                **info,
                'last_updated': datetime.now().isoformat()
            }
            metadata['last_updated'] = datetime.now().isoformat()
            self.metadata_file.write_text(json.dumps(metadata, indent=2))
            self.repo.index.add(['metadata.json'])
            return True
        except Exception as e:
            logger.error(f"Error updating metadata: {str(e)}")
            return False

    def create_branch(self, branch_name: str) -> bool:
        """
        Create a new branch.
        
        Args:
            branch_name (str): Name of the branch to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            current = self.repo.active_branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            logger.info(f"Created and checked out branch: {branch_name}")
            return True
        except GitCommandError as e:
            logger.error(f"Error creating branch: {str(e)}")
            return False

    def save_document(self, 
                     doc_id: str, 
                     content: str, 
                     author: str, 
                     version: str = "1.0",
                     tags: List[str] = None) -> bool:
        """
        Save a document to the repository.
        
        Args:
            doc_id (str): Unique identifier for the document
            content (str): Document content
            author (str): Author of the changes
            version (str): Version of the document
            tags (List[str]): Tags for categorizing the document
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory structure
            doc_dir = self.base_path / 'documents' / doc_id
            doc_dir.mkdir(parents=True, exist_ok=True)
            
            # Save document content
            doc_path = doc_dir / 'content.md'
            doc_path.write_text(content)
            
            # Update metadata
            metadata_update = {
                'author': author,
                'version': version,
                'tags': tags or [],
                'created_at': datetime.now().isoformat()
            }
            self._update_metadata(doc_id, metadata_update)
            
            # Commit changes
            self.repo.index.add([str(doc_path.relative_to(self.base_path))])
            commit_message = f"""
            Update document: {doc_id}
            Author: {author}
            Version: {version}
            Tags: {', '.join(tags) if tags else 'None'}
            """
            self.repo.index.commit(commit_message)
            
            logger.info(f"Successfully saved document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            return False

    def get_document_history(self, doc_id: str) -> List[Dict]:
        """
        Get the commit history for a specific document.
        
        Args:
            doc_id (str): Document identifier
            
        Returns:
            List[Dict]: List of commits with their details
        """
        try:
            doc_path = f'documents/{doc_id}/content.md'
            commits = []
            
            for commit in self.repo.iter_commits(paths=doc_path):
                commits.append({
                    'hash': commit.hexsha,
                    'author': commit.author.name,
                    'date': commit.committed_datetime.isoformat(),
                    'message': commit.message.strip()
                })
            
            return commits
        except Exception as e:
            logger.error(f"Error getting document history: {str(e)}")
            return []

    def get_document_version(self, doc_id: str, commit_hash: str) -> Optional[str]:
        """
        Get a specific version of a document.
        
        Args:
            doc_id (str): Document identifier
            commit_hash (str): Commit hash for the desired version
            
        Returns:
            Optional[str]: Document content at that version, or None if not found
        """
        try:
            doc_path = f'documents/{doc_id}/content.md'
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / doc_path
            return blob.data_stream.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error getting document version: {str(e)}")
            return None

    def compare_versions(self, doc_id: str, commit1: str, commit2: str) -> List[Dict]:
        """
        Compare two versions of a document.
        
        Args:
            doc_id (str): Document identifier
            commit1 (str): First commit hash
            commit2 (str): Second commit hash
            
        Returns:
            List[Dict]: List of differences between versions
        """
        try:
            doc_path = f'documents/{doc_id}/content.md'
            diff_index = self.repo.commit(commit1).tree.diff(
                self.repo.commit(commit2),
                paths=[doc_path]
            )
            
            changes = []
            for diff in diff_index:
                if diff.a_path == doc_path:
                    changes.append({
                        'old_content': diff.a_blob.data_stream.read().decode('utf-8'),
                        'new_content': diff.b_blob.data_stream.read().decode('utf-8'),
                        'change_type': diff.change_type
                    })
            
            return changes
        except Exception as e:
            logger.error(f"Error comparing versions: {str(e)}")
            return []

    def search_documents(self, query: str) -> List[Dict]:
        """
        Search for documents based on content or metadata.
        
        Args:
            query (str): Search query
            
        Returns:
            List[Dict]: Matching documents with their metadata
        """
        try:
            metadata = json.loads(self.metadata_file.read_text())
            results = []
            
            for doc_id, info in metadata['documents'].items():
                doc_path = self.base_path / 'documents' / doc_id / 'content.md'
                if doc_path.exists():
                    content = doc_path.read_text().lower()
                    if (query.lower() in content or
                        query.lower() in json.dumps(info).lower()):
                        results.append({
                            'doc_id': doc_id,
                            'metadata': info,
                            'preview': content[:200] + '...' if len(content) > 200 else content
                        })
            
            return results
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []

    def create_backup(self, backup_dir: str) -> bool:
        """
        Create a backup of the entire repository.
        
        Args:
            backup_dir (str): Directory to store the backup
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_dir) / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(self.base_path, backup_path)
            logger.info(f"Created backup at: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False

    def revert_changes(self, doc_id: str, commit_hash: str) -> bool:
        """
        Revert a document to a specific version.
        
        Args:
            doc_id (str): Document identifier
            commit_hash (str): Commit hash to revert to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_path = f'documents/{doc_id}/content.md'
            content = self.get_document_version(doc_id, commit_hash)
            
            if content is None:
                return False
            
            current_path = self.base_path / doc_path
            current_path.write_text(content)
            
            self.repo.index.add([doc_path])
            self.repo.index.commit(f"Reverted {doc_id} to version {commit_hash[:8]}")
            
            return True
        except Exception as e:
            logger.error(f"Error reverting changes: {str(e)}")
            return False

    def get_document_stats(self, doc_id: str) -> Dict:
        """
        Get statistics about a document's history.
        
        Args:
            doc_id (str): Document identifier
            
        Returns:
            Dict: Statistics about the document
        """
        try:
            commits = self.get_document_history(doc_id)
            metadata = json.loads(self.metadata_file.read_text())
            doc_info = metadata['documents'].get(doc_id, {})
            
            return {
                'total_revisions': len(commits),
                'first_created': commits[-1]['date'] if commits else None,
                'last_modified': commits[0]['date'] if commits else None,
                'authors': list(set(commit['author'] for commit in commits)),
                'current_version': doc_info.get('version'),
                'tags': doc_info.get('tags', [])
            }
        except Exception as e:
            logger.error(f"Error getting document stats: {str(e)}")
            return {}