🧬 PAH Bioremediation LLM Project 🤖

This repo consists of preliminary work steps to develop a large language model (LLM) specialized in polycyclic aromatic hydrocarbon (PAH) bioremediation.


📋 Project Flow

🔄 1. Data Preparation
    
    📄 PDF Processing: The scientific article is divided into 59 paragraphs using the pdf_spliter.py script
    
    💾 Data Storage: Segments are structured and saved in JSON format
    
    🎯 Purpose: Processing scientific content in a modular structure


🤖 2. Question-Answer Data Set Creation
    
    ⚙️ Main Script: The main.py controller script is run
    
    🌐 API Connection: Communication with the QWEN 1.5 7B Chat model via LM Studio
    
    ❓ Question Generation: Questions are created in 5 categories for each paragraph
    
    📊 Output: 295 question-answer pairs in the trainset_qa.csv file


📤 3. Data Set Loading
    
    🔄 Format Conversion: Converted to Stanford Alpaca format
    
    ☁️ Platform: Google Colaboratory environment is used
    
    📥 Loading: DataSetConvertAndPushHF script is used to import to HuggingFace


🎓 4. Model Training
    
    🔗 Connection: Dataset is connected via Unsloth framework
    
    🤖 Base Model: Meta-Llama-3.1-8B model is used
    
    🎯 Fine-tuning: Training with PAH bioremediation dataset


📦 5. Model Packaging and Distribution
    
    🗜️ Format: Packaged in GGUF format
    
    ⚡ Optimization: q4_k_m quantization is applied
    
    📤 Loading: Imported into HuggingFace model repository
    
    💻 Local Installation: Made accessible via LM Studio


📊 6. Performance Evaluation
    
    🔍 Comparison: Tested with general GPT models
    
    ChatGPT 
    
    DeepSeek 
    
    Mistral 


📈 Results:
    
    ✅ Demo Model: Specific, citational, short and focused answers
    
    ❌ General Models: Long, general and superficial information


🛠️ Technologies Used
    
    🐍 Python: Main programming language
    
    🤗 HuggingFace: Model and dataset platform
   
    💻 LM Studio: Local model execution environment
    
    ⚡ Unsloth: Fast model training framework
    
    ☁️ Google Colab: Cloud computing environment
    
    📊 GGUF: Model format and quantization
