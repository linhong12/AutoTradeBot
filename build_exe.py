#!/usr/bin/env python3
"""
交易机器人打包脚本
使用PyInstaller将bot打包成可执行文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


class BuildExecutor:
    """构建执行器"""
    
    def __init__(self):
        self.current_dir = Path(__file__).parent
        self.output_dir = self.current_dir / "dist"
        self.build_dir = self.current_dir / "build"
        self.main_script = self.current_dir / "main.py"
        self.icon_file = self.current_dir / "assets" / "icon.png"
        
    def check_dependencies(self):
        """检查依赖项"""
        print("检查依赖项...")
        
        # 检查PyInstaller是否安装
        try:
            import PyInstaller
            print(f"✓ PyInstaller已安装: {PyInstaller.__version__}")
        except ImportError:
            print("✗ PyInstaller未安装，正在安装...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
            print("✓ PyInstaller安装成功")
        
        # 检查其他依赖项
        required_packages = [
            "PyQt5",
            "matplotlib",
            "pandas",
            "numpy",
            "requests"
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✓ {package}已安装")
            except ImportError:
                print(f"✗ {package}未安装，正在安装...")
                subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
                print(f"✓ {package}安装成功")
    
    def clean_old_builds(self):
        """清理旧的构建文件"""
        print("清理旧的构建文件...")
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            print(f"✓ 已清理输出目录: {self.output_dir}")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print(f"✓ 已清理构建目录: {self.build_dir}")
    
    def build_exe(self, onefile=False, console=False):
        """构建可执行文件
        
        Args:
            onefile: 是否打包成单个文件
            console: 是否显示控制台窗口
        """
        print("开始构建可执行文件...")
        
        # 构建PyInstaller命令
        cmd = [
            sys.executable,
            "-m", "PyInstaller",
            "--name", "KronosBot",
            "--distpath", str(self.output_dir),
            "--workpath", str(self.build_dir),
            # 桌面应用特定配置
            "--noconsole",  # 明确指定无控制台窗口
            "--noupx",  # 禁用UPX压缩，避免可能的问题
        ]
        
        # 配置打包选项
        if onefile:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")
        
        # 添加图标
        if self.icon_file.exists():
            cmd.extend(["--icon", str(self.icon_file)])
        
        # 添加数据文件
        cmd.extend([
            "--add-data", f"assets;assets",
            "--add-data", f"config;config"
        ])
        
        # 添加主脚本
        cmd.append(str(self.main_script))
        
        print(f"执行命令: {' '.join(cmd)}")
        
        # 执行构建命令
        try:
            subprocess.run(cmd, check=True)
            print("\n✓ 构建成功!")
            
            # 显示构建结果
            if onefile:
                exe_file = self.output_dir / "KronosBot.exe"
                if exe_file.exists():
                    print(f"可执行文件位置: {exe_file}")
            else:
                exe_dir = self.output_dir / "KronosBot"
                if exe_dir.exists():
                    exe_file = exe_dir / "KronosBot.exe"
                    if exe_file.exists():
                        print(f"可执行文件位置: {exe_file}")
                        print(f"可执行文件目录: {exe_dir}")
        except subprocess.CalledProcessError as e:
            print(f"\n✗ 构建失败: {e}")
            return False
        
        return True


def main():
    """主函数"""
    print("=== Kronos交易机器人打包工具 ===")
    
    build_executor = BuildExecutor()
    
    # 检查依赖项
    try:
        build_executor.check_dependencies()
    except Exception as e:
        print(f"检查依赖项失败: {e}")
        return
    
    # 清理旧的构建文件
    build_executor.clean_old_builds()
    
    # 构建可执行文件（使用onedir模式，更稳定）
    print("\n构建配置:")
    print("- 模式: 目录模式 (onedir) - 更稳定")
    print("- 窗口: 无控制台窗口（纯桌面应用）")
    print("- 图标: 使用assets/icon.png")
    print("- 数据: 包含assets和config目录")
    print("- 配置: 禁用UPX压缩，避免可能的问题")
    
    success = build_executor.build_exe(onefile=False)
    
    if success:
        print("\n=== 打包完成 ===")
        print("您可以在dist/KronosBot目录中找到可执行文件")
        print("建议: 运行前请确保config目录中有正确的API密钥配置")
    else:
        print("\n=== 打包失败 ===")


if __name__ == "__main__":
    main()
