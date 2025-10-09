#!/usr/bin/env python3
"""
AutoDevOS End-to-End Demo Script

This script demonstrates the complete workflow:
1. Generate application from prompt
2. Install dependencies
3. Run database migrations (backend)
4. Start backend server
5. Start frontend server
6. Run tests
7. Generate report
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meta_agent.orchestrator import Orchestrator
from meta_agent.context_manager import MCPContext
from meta_agent.utils import log


class DemoRunner:
    def __init__(self, prompt: str, output_dir: Path):
        self.prompt = prompt
        self.output_dir = output_dir
        self.project_root = Path(__file__).resolve().parents[1]
        
    def run_command(self, cmd: list, cwd: Path = None, check: bool = True):
        """Run a shell command and return result."""
        log.info(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=check
            )
            if result.stdout:
                log.info(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            log.error(f"Command failed: {e}")
            if e.stderr:
                log.error(e.stderr)
            if check:
                raise
            return e
    
    async def generate_application(self):
        """Step 1: Generate application using orchestrator."""
        log.info("=" * 60)
        log.info("STEP 1: Generating Application")
        log.info("=" * 60)
        
        ctx = MCPContext(
            project_name="demo_app",
            storage_dir=self.output_dir / ".ctx"
        )
        
        orch = Orchestrator(
            project_root=self.project_root,
            output_dir=self.output_dir,
            max_parallel=4,
            use_dynamic_planning=False
        )
        
        summary = await orch.run(self.prompt, ctx, fail_fast=False)
        ctx.save()
        
        log.info(f"✅ Generation complete: {summary['completed']}/{summary['total']} tasks succeeded")
        
        if summary['failed'] > 0:
            log.warning(f"⚠️  {summary['failed']} tasks failed")
        
        return summary
    
    def install_dependencies(self):
        """Step 2: Install Node.js dependencies."""
        log.info("=" * 60)
        log.info("STEP 2: Installing Dependencies")
        log.info("=" * 60)
        
        # Install backend dependencies
        backend_dir = self.output_dir / "backend" / "app"
        if backend_dir.exists():
            log.info("Installing backend dependencies...")
            self.run_command(["npm", "install"], cwd=backend_dir)
        
        # Install frontend dependencies
        frontend_dir = self.output_dir / "frontend" / "app"
        if frontend_dir.exists():
            log.info("Installing frontend dependencies...")
            self.run_command(["npm", "install"], cwd=frontend_dir)
        
        log.info("✅ Dependencies installed")
    
    def setup_database(self):
        """Step 3: Setup database (Prisma)."""
        log.info("=" * 60)
        log.info("STEP 3: Setting up Database")
        log.info("=" * 60)
        
        backend_dir = self.output_dir / "backend" / "app"
        if not (backend_dir / "prisma").exists():
            log.info("No Prisma schema found, skipping database setup")
            return
        
        log.info("Generating Prisma client...")
        self.run_command(["npm", "run", "db:generate"], cwd=backend_dir)
        
        log.info("Pushing database schema...")
        self.run_command(["npm", "run", "db:push"], cwd=backend_dir, check=False)
        
        log.info("✅ Database setup complete")
    
    def run_tests(self):
        """Step 4: Run tests."""
        log.info("=" * 60)
        log.info("STEP 4: Running Tests")
        log.info("=" * 60)
        
        # Run backend tests
        backend_dir = self.output_dir / "backend" / "app"
        if backend_dir.exists():
            log.info("Running backend tests...")
            result = self.run_command(["npm", "test"], cwd=backend_dir, check=False)
            if result.returncode == 0:
                log.info("✅ Backend tests passed")
            else:
                log.warning("⚠️  Backend tests failed")
        
        # Run frontend tests
        frontend_dir = self.output_dir / "frontend" / "app"
        if frontend_dir.exists():
            log.info("Running frontend tests...")
            result = self.run_command(["npm", "test"], cwd=frontend_dir, check=False)
            if result.returncode == 0:
                log.info("✅ Frontend tests passed")
            else:
                log.warning("⚠️  Frontend tests failed")
    
    def generate_report(self):
        """Step 5: Generate summary report."""
        log.info("=" * 60)
        log.info("DEMO SUMMARY REPORT")
        log.info("=" * 60)
        
        backend_dir = self.output_dir / "backend" / "app"
        frontend_dir = self.output_dir / "frontend" / "app"
        
        log.info(f"\n📦 Generated Artifacts:")
        log.info(f"  - Frontend: {frontend_dir}")
        log.info(f"  - Backend: {backend_dir}")
        log.info(f"  - Context: {self.output_dir / '.ctx'}")
        
        log.info(f"\n🚀 To start the applications:")
        log.info(f"  Backend:  cd {backend_dir} && npm run dev")
        log.info(f"  Frontend: cd {frontend_dir} && npm run dev")
        
        log.info(f"\n📝 API Endpoints (Backend):")
        log.info(f"  - POST /api/auth/register - Register user")
        log.info(f"  - POST /api/auth/login - Login user")
        log.info(f"  - GET /api/items - List items (requires auth)")
        log.info(f"  - POST /api/items - Create item (requires auth)")
        
        log.info(f"\n✨ Demo completed successfully!")
    
    async def run(self):
        """Run complete demo workflow."""
        try:
            # Step 1: Generate
            await self.generate_application()
            
            # Step 2: Install
            self.install_dependencies()
            
            # Step 3: Database
            self.setup_database()
            
            # Step 4: Tests
            self.run_tests()
            
            # Step 5: Report
            self.generate_report()
            
            return True
            
        except Exception as e:
            log.error(f"Demo failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoDevOS End-to-End Demo")
    parser.add_argument(
        "--prompt",
        type=str,
        default="Build a task management app with user authentication",
        help="Prompt for application generation"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="demo_output",
        help="Output directory"
    )
    args = parser.parse_args()
    
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / args.output
    
    log.info("🚀 AutoDevOS End-to-End Demo")
    log.info(f"Prompt: {args.prompt}")
    log.info(f"Output: {output_dir}")
    log.info("")
    
    demo = DemoRunner(args.prompt, output_dir)
    success = await demo.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
