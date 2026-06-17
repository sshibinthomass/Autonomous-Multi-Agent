import os
import sys
import subprocess

def main():
    llm_dir = os.path.join("orchestrator_agent", "llms")
    llm_files = [
        "anthropic_llm.py",
        "gemini_llm.py",
        "groq_llm.py",
        "ollama_llm.py",
        "openai_llm.py"
    ]
    
    if os.environ.get("CI") == "true":
        print("Running in CI environment. Skipping Anthropic and OpenAI checks.")
        llm_files = [f for f in llm_files if f not in ("anthropic_llm.py", "openai_llm.py")]
    
    print("=========================================")
    print("Starting LLM Verifications...")
    print("=========================================")
    
    failed = False
    for llm_file in llm_files:
        path = os.path.join(llm_dir, llm_file)
        if not os.path.exists(path):
            print(f"❌ {llm_file} not found at {path}!")
            failed = True
            continue
            
        print(f"Running verification for {llm_file}...")
        
        # Run the script as a subprocess using the current python executable
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ {llm_file} verification FAILED!")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout.strip()}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr.strip()}")
            print("-----------------------------------------")
            failed = True
        else:
            print(f"✅ {llm_file} verification PASSED.")
            if result.stdout:
                # Optionally print a truncated version of the success response or just log it
                first_line = result.stdout.strip().split('\n')[0]
                print(f"   Output snippet: {first_line}")
            print("-----------------------------------------")
            
    if failed:
        print("❌ Verification failed! One or more LLMs had errors.")
        sys.exit(1)
    else:
        print("✅ All LLMs verified successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
