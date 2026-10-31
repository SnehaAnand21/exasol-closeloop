"""
CloseLoop: PDF Exporter from PowerPoint PPTX
"""
import os
import sys

ppt_path = os.path.abspath("docs/CloseLoop_Pitch_Deck.pptx")
pdf_path = os.path.abspath("docs/CloseLoop_Pitch_Deck.pdf")

try:
    import win32com.client
    powerpoint = win32com.client.DispatchEx("PowerPoint.Application")
    deck = powerpoint.Presentations.Open(ppt_path, WithWindow=False)
    deck.SaveAs(pdf_path, 32)  # 32 = ppSaveAsPDF
    deck.Close()
    powerpoint.Quit()
    print("[+] PDF exported successfully to:", pdf_path)
except Exception as e:
    print("[!] PowerPoint COM not available locally:", e)
    print("[*] Note: CloseLoop_Pitch_Deck.pptx can be opened in PowerPoint or Google Slides and downloaded as PDF with File -> Download -> PDF.")
