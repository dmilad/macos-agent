#!/bin/bash
set -e

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY environment variable not set"
    echo ""
    echo "Please set it with:"
    echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
    echo ""
    echo "Or the UI will prompt you to enter it."
fi

# Set screen dimensions (your macOS screen size)
export WIDTH=1440
export HEIGHT=900

echo "🚀 Starting macOS Agent..."
echo "📱 Screen resolution: ${WIDTH}x${HEIGHT}"
echo "🌐 Open http://localhost:8501 in your browser"
echo ""

# Run Streamlit
streamlit run computer_use_demo/streamlit.py
