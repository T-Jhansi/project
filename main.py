from git_integration import GitManager
from collaboration import CollaborationManager
from api_docs import APIDocumentationGenerator
import streamlit as st
import logging
from auth import Auth
from code_analyzer import CodeAnalyzer
from document_generator import DocumentGenerator
from export_utils import DocumentExporter
from history_manager import HistoryManager
import os
import tempfile

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
auth = Auth()
doc_generator = DocumentGenerator()
history_manager = HistoryManager()

git_integration = GitManager()
collab_manager = CollaborationManager()
api_doc_generator = APIDocumentationGenerator()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'documentation' not in st.session_state:
    st.session_state['documentation'] = None
if 'export_ready' not in st.session_state:
    st.session_state['export_ready'] = False

def main():
    st.title("Advanced Code Documentation Generator")
    
    # Add notifications to sidebar
    if st.session_state.get('logged_in'):
        with st.sidebar:
            notifications = collab_manager.get_notifications(st.session_state['username'])
            unread = [n for n in notifications if not n['read']]
            if unread:
                st.warning(f"You have {len(unread)} unread notifications")
                if st.button("View Notifications"):
                    for notif in unread:
                        st.info(notif['message'])
                        if st.button(f"Mark as Read {notif['id']}"):
                            collab_manager.mark_notification_read(notif['id'])
    
    # Authentication section
    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.header("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                if auth.login_user(username, password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with tab2:
            st.header("Register")
            new_username = st.text_input("Username", key="reg_username")
            new_password = st.text_input("Password", type="password", key="reg_password")
            if st.button("Register"):
                if auth.register_user(new_username, new_password):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Username already exists")
    
    else:
        st.sidebar.success(f"Logged in as {st.session_state['username']}")
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.rerun()
        
        # Documentation type selector
        doc_type = st.radio(
            "Select Documentation Type",
            ["Regular Code", "API Documentation"]
        )
        
        # Main documentation interface
        code_input = st.text_area("Paste your Python code here:", height=300)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate Documentation"):
                if code_input.strip():
                    try:
                        # Analyze code
                        functions, classes, relationships = CodeAnalyzer.analyze_code_structure(code_input)
                        analysis = {
                            'functions': functions,
                            'classes': classes,
                            'relationships': relationships
                        }
                        
                        # Generate documentation
                        documentation = doc_generator.generate_documentation(code_input, analysis)
                        
                        # Clean up unwanted content (e.g., <think>) from documentation
                        documentation = documentation.lstrip('<think>').lstrip()  # Remove leading <think> and whitespace
                        
                        # Store in session state
                        st.session_state['documentation'] = documentation
                        st.session_state['export_ready'] = True
                        
                        # Log the generated documentation for debugging purposes
                        logger.debug("Generated Documentation: %s", documentation)
                        
                        # Save to history
                        history_manager.add_entry(
                            st.session_state['username'],
                            code_input,
                            documentation
                        )
                        
                        # Display results
                        st.write("### Code Analysis:")
                        st.write(f"**Functions Found:** {', '.join(functions) if functions else 'None'}")
                        st.write(f"**Classes Found:** {', '.join(classes) if classes else 'None'}")
                        st.write("### Generated Documentation:")
                        st.markdown(documentation)
                    
                    except Exception as e:
                        st.error(f"Error processing code: {str(e)}")
                        logger.error(f"Error processing code: {str(e)}", exc_info=True)
            
            # Export options (separate from the Generate Documentation button)
            if st.session_state['export_ready']:
                st.subheader("Export Documentation")
                export_format = st.selectbox(
                    "Export Format",
                    ["PDF", "DOCX"]
                )
                
                export_button = st.button("Export Documentation")
                if export_button:
                    try:
                        documentation = st.session_state['documentation']
                        if not documentation:
                            st.error("No documentation to export. Generate documentation first.")
                            st.stop()
                            
                        with st.spinner(f"Generating {export_format} file..."):
                            # Generate a temporary file with a unique name
                            temp_dir = tempfile.gettempdir()
                            
                            if export_format == "PDF":
                                file_path = DocumentExporter.export_pdf(documentation, output_dir=temp_dir)
                                mime_type = "application/pdf"
                            else:
                                file_path = DocumentExporter.export_docx(documentation, output_dir=temp_dir)
                                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            
                            # Log the file path for debugging
                            logger.info(f"Generated file at: {file_path}")
                            
                            # Check if file exists
                            if not os.path.exists(file_path):
                                st.error(f"Failed to generate {export_format} file: File not created")
                                logger.error(f"File not found at: {file_path}")
                                st.stop()
                            
                            # Get file size for verification
                            file_size = os.path.getsize(file_path)
                            logger.info(f"File size: {file_size} bytes")
                            
                            if file_size == 0:
                                st.error(f"Generated {export_format} file is empty")
                                logger.error(f"File is empty: {file_path}")
                                st.stop()
                                
                            # Read file and offer download
                            with open(file_path, 'rb') as f:
                                file_content = f.read()
                                file_name = f"documentation.{export_format.lower()}"
                                
                                st.download_button(
                                    label=f"Download {export_format}",
                                    data=file_content,
                                    file_name=file_name,
                                    mime=mime_type
                                )
                                
                            st.success(f"{export_format} file generated successfully!")
                            
                    except Exception as e:
                        st.error(f"Error exporting documentation: {str(e)}")
                        logger.error(f"Export error: {str(e)}", exc_info=True)
        
        with col2:
            st.header("Documentation History")
            history = history_manager.get_user_history(st.session_state['username'])
            for entry in history:
                with st.expander(f"Documentation from {entry[4]}"):
                    st.code(entry[2], language='python')
                    st.markdown(entry[3])

if __name__ == "__main__":
    main()