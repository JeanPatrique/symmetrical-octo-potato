from threading import Thread, Lock
from time import time, sleep
from tkinter.messagebox import showwarning
from numpy import array
from pyautogui import screenshot
from pynput import keyboard
from tkinter import PhotoImage, Tk, Button, Label
from pickle import Pickler



class Manager():
    def __init__(self, fps=60) -> None:
        self.running=True
        self.lockRunning=Lock()

        self.firstTime=time()
        self.fps=fps

    def arrete(self):
        with self.lockRunning:
            self.running=False
    
    def continu(self)->bool:
        with self.lockRunning:
            return self.running


class KeyboardManager(Thread, Manager):
    def __init__(self) -> None:
        Thread.__init__(self, daemon=True)
        Manager.__init__(self)

        self.touches=list()
        self.lockTouches=Lock()

    def dumpNewTouch(self, key, forceDumping=False):
        if len(self.touches)>100 or forceDumping:
            with self.lockTouches:
                flushThread=Thread(target=flushTouch, args=[self.touches, self.firstTime, time()])
                self.touches=list()
            flushThread.start()
            self.firstTime=time()
        else:
            self.touches.append((key, time()))

    def run(self)->None:
        with keyboard.Events() as events:
            for event in events:
                if self.continu():
                    self.dumpNewTouch(event)
                else:
                    self.dumpNewTouch(event, forceDumping=True)
                    break

class ScreenManager(Thread, Manager):
    def __init__(self, fps=60) -> None:
        Thread.__init__(self, daemon=True)
        Manager.__init__(self, fps=fps)

        self.images = list()
        self.lockImages=Lock()
        self.timeLastScreen=time()

    def takeScreenShot(self):
        if time()-self.timeLastScreen>1/self.fps:
            with self.lockImages:
                self.images.append((array(screenshot()), time()))
            self.timeLastScreen=time()

    def saveImages(self):
        with self.lockImages:
            # on lance le 'flush' des images dans un nouveau processus
            flushThread = Thread(target=flushImages, args=[self.images, self.firstTime, time()])
            self.images=list()
        flushThread.start()
        self.firstTime=time()
        
    def run(self)->None:
        i=0
        while self.continu():
            if len(self.images)>100: # si on a plus de 100 images enregistrer :
                self.saveImages()
            self.takeScreenShot()
        self.saveImages()

class SoundManager(Thread, Manager):
    def __init__(self) -> None:
        Thread.__init__(self,daemon=True)
        Manager.__init__(self)

    def run(self):pass


# ---------------------------------------------------- fonction de flush
def flushImages(images, Tdebut, Tfin):
    with open(f"../data/raw/images/ecran_{Tdebut}_{Tfin}", "wb") as fichier:
        pickler=Pickler(fichier)
        pickler.dump(images)

def flushTouch(touches, Tdebut, Tfin):
    with open(f"../data/raw/touches/clavier_{Tdebut}_{Tfin}", "wb") as fichier:
        pickler=Pickler(fichier)
        pickler.dump(touches)
# ---------------------------------------------------- fonction de flush
# ---------------------------------------------------- fonction de controle de l'enregistrement
class Monitor(Thread):
    def __init__(self, ecran, clavier, son, label=None, rafraichissmentParSec=1) -> None:
        super().__init__(daemon=True)
        #ressources
        self.ecran=ecran
        self.clavier=clavier
        self.son=son
        
        # monitoring
        self.label=label
        self.update=rafraichissmentParSec
        #systeme d'arrêt
        self.running=False
        self.lockRunning=Lock()

    def launch(self):
        """active l'enregistrement"""
        # démarrage clavier
        if self.clavier:
            self.clavier.start()
        if self.ecran:
            self.ecran.start()
        if self.son:
            self.son.start()

    def arrete(self):
        """arrête l'enregistrement"""
        self.clavier.arrete()
        self.ecran.arrete()
        
        #with self.lockRunning:
        #    self.running=False

    def arretTotale(self):
        self.clavier.arrete()
        self.ecran.arrete()
        
        self.clavier.join()
        self.ecran.join()
        
        with self.lockRunning:
            self.running=False
    
    def run(self):
        with self.lockRunning:
            self.running=True
        while self.continuing() :
            clavierAlive=False
            ecranAlive=False
            sonAlive=False
            if self.clavier!=None:
                if self.clavier.is_alive():
                    clavierAlive=True
            if self.ecran!=None:
                if self.ecran.is_alive():
                    ecranAlive=True
            if self.son!=None:
                if self.son.is_alive():
                    sonAlive=True
                      
            self.label.config(text=f"Clavier : {'[En ligne]' if clavierAlive else '[Hors ligne]'}\nEcran : {'[En ligne]' if ecranAlive else '[Hors ligne]'}\nSon : {'[En ligne]' if sonAlive else '[Hors ligne]'}")
                        
            sleep(1/self.update)

    def continuing(self):
        with self.lockRunning:
            return self.running
# ---------------------------------------------------- fonction de controle de l'enregistrement
# ---------------------------------------------------- GUI 
class Gui():
    """une implémentation graphique du recorder"""
    def __init__(self) -> None:
        # ressources
        self.monitor=None    
        self.ecran=ScreenManager()
        self.clavier=KeyboardManager()
        self.son=SoundManager()

        # GUI
        self.root=Tk()
        self.root.title="Enregistreur de sources"
        #self.root.iconphoto(True, PhotoImage(file="etc/icon.png"))
        self.root.resizable(height=False, width=False)

        self.labelStatus=Label(self.root, text="Opérationnel : en attente de nouvelle commande")
        self.labelMonitoring=Label(self.root, text="")
        self.buttonStart=Button(self.root, text="Start", width=20, command=self.start)
        self.buttonStop=Button(self.root, text="Stop", width=20, command=self.arrete)
        self.buttonQuitter=Button(self.root, text="Quitter", width=40, command=self.arretTotale)

        self.labelStatus.grid(column=0, row=0, columnspan=2)
        self.labelMonitoring.grid(column=0, row=1, columnspan=2)
        self.buttonStart.grid(column=0, row=2)
        self.buttonStop.grid(column=1, row=2)
        self.buttonQuitter.grid(column=0, row=3, columnspan=2)

        showwarning(title="ATTENTION/WARNING", message="ATTENTION : ce script est très gourmand en ressources : \n\nRAM : +2Go (uniquement dédier a ce script)\nDISQUE : 170Mo/s (uniquement dédier a ce script)\n\nUN PROBLEME AUSSI : POUR ETEIENDRE LA SOURCES 'CLAVIER' APPUYEZ SUR UNE TOUCHE APRES STOP")
        
        self.root.mainloop()

    def arrete(self):
        if self.monitor:
            self.labelStatus.config(text="mise en pause du moniteur")
            self.monitor.arrete()
            self.labelStatus.config(text="En pause : les enregistrements sont arrêté")
        else:
            self.labelStatus.config(text="Problème -> rien ne peut être arrêté :O -> vous n'avez rien démarré :p")
    def start(self):
        if not self.monitor:
            # initialisation du moniteur
            self.labelStatus.config(text="Initialisation du moniteur")
            self.monitor=Monitor(self.ecran, self.clavier, None, self.labelMonitoring)
            self.labelStatus.config(text="En fonction : enregistrement activé")
            self.monitor.start()
        elif not self.monitor.is_alive():
            self.monitor.start()
            
        self.monitor.launch()
    def arretTotale(self):
        if self.monitor:
            self.monitor.arretTotale()
            self.monitor.join()
        self.root.destroy()
# ---------------------------------------------------- GUI 
# ---------------------------------------------------- ALIVEEEEEEEEEEEEEEEE
if __name__=="__main__":
    app=Gui()
# ---------------------------------------------------- ALIVEEEEEEEEEEEEEEEE

