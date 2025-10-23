#!/bin/bash
set -e

echo "🚀 Setting up macOS Agent..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create virtual environment with Python 3.11+
echo "📦 Creating virtual environment with uv..."
uv venv

# Activate virtual environment
echo "🔧 Installing dependencies..."
source .venv/bin/activate

# Install dependencies using uv
uv pip install -e ".[dev]"

# Create config directory
echo "📁 Creating config directory..."
mkdir -p ~/.anthropic

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Set your Anthropic API key:"
echo "   export ANTHROPIC_API_KEY='your-api-key-here'"
echo ""
echo "3. Run the agent:"
echo "   streamlit run computer_use_demo/streamlit.py"
echo ""
echo "⚠️  IMPORTANT: macOS will ask for Accessibility permissions."
echo "   Go to System Settings > Privacy & Security > Accessibility"
echo "   and grant access to Terminal or Python when prompted."
