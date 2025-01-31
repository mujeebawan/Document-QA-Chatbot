
#os.environ["OPENAI_API_KEY"] = "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"
import os
import streamlit as st
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter 
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from langchain.docstore.document import Document
import tempfile

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY_HERE"


# Configure the layout of the Streamlit app
st.set_page_config(layout="wide")

# Custom CSS for centering and styling messagess
st.markdown("""
    <style>
        .main {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }
        .stApp {
            max-width: 1400px;
            margin: 0 auto;
        }
        .chat-message {
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .user-message {
            background-color: #f0f2f6;
        }
        .bot-message {
            background-color: #ffffff;
            border: 1px solid #e6e6e6;
        }
        div[data-testid="stForm"] {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

def process_document(uploaded_file):
    """
    Processes an uploaded document (PDF or TXT), splits it into chunks, and
    creates a FAISS vectorstore for similarity-based retrieval.
    """

    #Save the uploaded file as a temporary file for processing.
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    # Load the document based on its type
    if uploaded_file.name.endswith('.pdf'):
        loader = PyPDFLoader(tmp_path)
    else:
        loader = TextLoader(tmp_path)

    documents = loader.load()

    # Split the document into chunks for better embedding retrieval
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    docs = text_splitter.split_documents(documents)

    # Create a vectorstore for the document using OpenAI embeddings
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)
    os.unlink(tmp_path)  # Delete the temporary file after processing
    return vectorstore

def create_conversation_chain(vectorstore):
    """
    Creates a conversational retrieval chain using OpenAI's language model
    and a retriever backed by the vectorstore.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.6)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    # Initialize the conversational retrieval chain
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
    )
    return conversation_chain

def update_vectorstore_with_qa(vectorstore, question, answer):
    """
    Appends the question-answer pair to the vectorstore to include it in
    future retrievals.
    """
    # Combine the question and answer into a single string
    qa_pair = f"Q: {question}\nA: {answer}"

    # Create a new Document object for the Q&A pair
    new_doc = Document(page_content=qa_pair)

    # Use the CharacterTextSplitter to split the document if necessary
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    new_docs = text_splitter.split_documents([new_doc])

    # Add the new documents to the vectorstore
    vectorstore.add_documents(new_docs)

def main():
    """
    Main function to run the Streamlit app. Handles file upload, document processing,
    chat interactions, and dynamic vectorstore updates.
    """
    st.markdown("<h1 style='text-align: center;'>Document QA Chatbot</h1>", unsafe_allow_html=True)

   

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

#Allow users to upload files. On button press, process the document and set up the conversation chain.
    col1, col2, col3 = st.columns([0.15, 0.7, 0.15])
    with col2:
        uploaded_file = st.file_uploader("Upload a document (PDF or TXT)", type=["pdf", "txt"])
        if uploaded_file:
            if st.button("Process Document", key="process_btn"):
                with st.spinner("Processing document..."):
                    vectorstore = process_document(uploaded_file)
                    st.session_state.vectorstore = vectorstore
                    st.session_state.conversation = create_conversation_chain(vectorstore)
                    st.success("Document processed successfully!")

#Display previous chat history in a styled format.
    col1, col2, col3 = st.columns([0.15, 0.7, 0.15])
    with col2:
        if st.session_state.chat_history:
            for role, message in st.session_state.chat_history:
                if role == "You":
                    st.markdown(f"<div class='chat-message user-message'><b>👤 You:</b> {message}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-message bot-message'><b>🤖 Bot:</b> {message}</div>", unsafe_allow_html=True)

#Accept user queries, process them through the conversation chain, and display the chatbot’s response.
        if st.session_state.conversation:
            with st.form(key="chat_form", clear_on_submit=True):
                user_question = st.text_input("Ask a question about your document:", key="question_input")
                submit_button = st.form_submit_button("Send")

                if submit_button and user_question:
                    with st.spinner("Thinking..."):
                        response = st.session_state.conversation({"question": user_question})
                        answer = response["answer"]

                        st.session_state.chat_history.append(("You", user_question))
                        st.session_state.chat_history.append(("Bot", answer))

##Append Q&A pairs to the vectorstore for continuous learning.
                        if st.session_state.vectorstore:
                            update_vectorstore_with_qa(st.session_state.vectorstore, user_question, answer)

                        st.rerun()

if __name__ == "__main__":
    main()
