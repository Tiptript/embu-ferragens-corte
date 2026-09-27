#!/bin/bash
# Script de inicialização automática para Azure App Service (Linux)
python -m streamlit run app_streamlit.py --server.port 8000 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
