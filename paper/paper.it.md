---
title: "La regola del 5x: come scegliere il terzo stadio di una cascata di modelli governata dalla fiducia"
subtitle: "Uno studio in simulazione e un protocollo per i modelli reali"
author: "Giovanni Simonetti"
date: "Rapporto tecnico, bozza 0.1, ottobre 2026"
lang: it
abstract: |
  In una cascata di modelli risponde prima un modello piccolo, e la richiesta sale a un modello più grande solo quando una fiducia tarata resta sotto una soglia. Lavori recenti mostrano che due livelli di modelli serviti in locale risparmiano un terzo o più del calcolo a parità di accuratezza. Questo rapporto si pone la domanda pratica successiva: quando una cascata dovrebbe avere un terzo stadio, e quale? Confrontiamo un modello intermedio e uno stadio di regole deterministiche su un carico di lavoro sintetico, al variare della scala dei costi, della qualità del segnale di fiducia e della quota di richieste facili. Ne esce una regola pratica, la regola del 5x. Quando i modelli vicini distano meno di 5x nel costo, un modello intermedio perde calcolo in 36 carichi simulati su 45, fino a 24 punti, mentre uno stadio di regole che risolve il 30% delle richieste ne guadagna fino a 18. Da 5x in su un modello intermedio conviene solo quando il segnale di fiducia è debole. Ogni numero è simulato; nessun modello reale è stato eseguito. Pubblichiamo il codice che riproduce ogni numero, un planner e un calcolatore per il browser, e un protocollo per provare la regola su modelli reali, con l'indicazione di cosa la smentirebbe.
geometry: margin=2.4cm
fontsize: 10.5pt
linestretch: 1.08
colorlinks: true
linkcolor: "black"
urlcolor: "blue"
header-includes:
  - \usepackage{booktabs}
  - \setlength{\parskip}{0.45em}
  - \setlength{\parindent}{0pt}
---

# 1. Introduzione

Far girare un modello linguistico grande su ogni richiesta è uno spreco quando la maggior parte delle richieste è facile. Una cascata affronta il problema: un modello piccolo risponde per primo, dichiara quanto è sicuro e passa la richiesta a un modello più grande solo quando quella fiducia è troppo bassa. Su hardware locale il risparmio è concreto: calcolo, energia e latenza su macchine già pagate.

L'idea è consolidata. FrugalGPT [1] ha introdotto le cascate di API di modelli linguistici. Lavori più recenti tarano la fiducia prima di usarla e girano su modelli aperti serviti in locale: UCCI [2] riporta una riduzione dei costi del 31% con due modelli e taratura isotonica, e Conformal Cascade [3] il 43% con garanzie formali di accuratezza. Entrambi sono valutati con due livelli.

Chi ha due livelli in funzione si trova davanti il passo successivo: aggiungerne un terzo. I candidati sono due. Uno è un modello intermedio, fra il piccolo e il grande. L'altro non è un modello: è uno stadio deterministico di ricerche esatte e regole fisse, che risolve ciò che può prima che giri un modello. I lavori pubblicati dicono poco su quale scegliere, o su quando non aggiungere nulla.

Questo rapporto offre una prima risposta, ottenuta in simulazione:

- **Una regola di decisione per il terzo stadio**, la regola del 5x, basata sul rapporto di costo fra modelli vicini e sulla qualità del segnale di fiducia.
- **Uno stadio di regole deterministiche trattato come stadio a pieno titolo**, confrontato con un modello intermedio sulle stesse richieste.
- **Un planner** che trasforma quattro numeri misurabili in una rosa di progetti da provare, disponibile da riga di comando e nel browser.
- **Un protocollo per i modelli reali**, con gli esiti che smentirebbero la regola dichiarati in anticipo.

I limiti vanno detti con chiarezza. Cascate, fiducia tarata e instradamento su modelli locali sono lavori precedenti, e questo rapporto non li rivendica. Il metodo è stato raggiunto in modo indipendente e poi confrontato con la letteratura. Tutti i risultati sono simulati su dati sintetici, e la regola è un'ipotesi da mettere alla prova, non una scoperta su sistemi reali.

# 2. Lavori correlati

**Cascate e instradamento.** FrugalGPT [1] mette in catena API di modelli e si ferma alla prima risposta accettabile. AutoMix [7] usa l'autoverifica per decidere quando salire. UCCI [2] e Conformal Cascade [3] tarano il segnale di fiducia, rispettivamente con regressione isotonica e previsione conforme, e valutano su modelli a pesi aperti serviti in locale. CARGO [4] e i token di confidenza [5] studiano più in generale l'instradamento guidato dalla fiducia, e [6] esamina quando i modelli sanno di non sapere. Conformal Cascade definisce uno schema a più livelli ma lo valuta con due.

**Eliminazione a stadi.** Scegliere fra molte opzioni con un budget fisso eliminando per stadi è il tema di Sequential Halving [8], delle sue generalizzazioni [9, 10] e di Hyperband [11], e risale alla selezione a più stadi in statistica [12]. Il repository applica la stessa logica alla scelta fra prompt o configurazioni candidate; quegli esperimenti sono riassunti nella sezione 7.

**Statistica.** La taratura per fasce e la sua misura seguono la pratica corrente [13]. Il test di taratura usato qui è il test chi quadro di bontà dell'adattamento nella forma di Hosmer e Lemeshow [14].

# 3. Impostazione

## 3.1 Carico di lavoro e modelli

Ogni richiesta ha una difficoltà latente $d$. Una quota $\pi$ delle richieste è facile, con $d \sim N(-2{,}5;\ 0{,}5^2)$; il resto è difficile, con $d \sim N(1;\ 1)$.

Tre modelli hanno capacità $a = (1{,}0;\ 1{,}8;\ 2{,}4)$: piccolo, medio e grande. Il modello $f$ risponde correttamente quando $a_f - d + \varepsilon > 0$, con $\varepsilon \sim N(0;\ 1)$. Con il 70% di richieste facili i tre modelli da soli raggiungono l'85%, il 91% e il 95% di accuratezza.

Ogni modello emette anche un segnale di fiducia grezzo

$$q_f = (a_f - d) + s\,z, \qquad z \sim N(0;\ 1).$$

Il rumore $s$ fissa la qualità del segnale: 0,5 è detto buono, 1,0 medio, 1,5 debole. In termini misurabili, con il 70% di richieste facili il segnale del modello piccolo separa le sue risposte giuste da quelle sbagliate con un'area sotto la curva ROC di circa 0,96, 0,94 e 0,91.

I costi sono calcolo relativo per richiesta. Per studiare la distanza fra i modelli con un solo parametro, la maggior parte degli esperimenti usa scale della forma $1 : r : r^2$, così che $r$ è il rapporto di costo fra modelli vicini.

## 3.2 Taratura e instradamento

Il segnale grezzo non si usa mai direttamente. Su un campione di taratura viene diviso in 200 fasce per quantili, e la fiducia tarata di una fascia è la frequenza osservata di risposte corrette al suo interno.

Gli stadi girano in ordine. La risposta di uno stadio è accettata quando la sua fiducia tarata raggiunge una soglia $\theta$; altrimenti la richiesta prosegue. L'ultimo stadio risponde sempre. La soglia si sceglie in una griglia fissa come il valore con il costo medio più basso sul campione di taratura, fra quelli che tengono l'accuratezza entro mezzo punto dal solo modello grande.

Tutti i numeri riportati vengono da un campione di prova indipendente di 300.000 richieste. Il risparmio è $1 - \text{costo} / c_{\text{grande}}$: la quota di calcolo risparmiata rispetto a far girare il modello grande su tutto.

## 3.3 Lo stadio di regole

Uno stadio di regole gira prima dei modelli. Risolve una quota di tutte le richieste, la copertura, e passa avanti il resto. Nella simulazione è idealizzato: scatta solo sulle richieste facili, è accurato al 99,5% su ciò che risolve e costa l'1% del calcolo del modello piccolo, pagato da ogni richiesta.

## 3.4 Progetti a confronto

Il riferimento è il solo modello grande. Il progetto a due stadi è piccolo poi grande. I progetti a tre stadi sono piccolo, medio, grande, e regole, piccolo, grande. Ogni confronto usa le stesse richieste simulate per tutti i progetti, e i guadagni sono espressi in punti di risparmio rispetto al progetto a due stadi.

# 4. Risultati

## 4.1 Il risparmio lo decide il carico di lavoro

La tabella 1 mostra il risparmio con una scala di costi ampia. La quota di richieste facili ne decide la gran parte: senza richieste facili una cascata non risparmia quasi nulla o costa di più, con il 90% risparmia dal 77% al 92%. Il metodo non può creare un risparmio che il carico non contiene.

| Richieste facili | Segnale buono, 3 stadi | Segnale buono, 2 stadi | Segnale debole, 3 stadi | Segnale debole, 2 stadi |
|:--|--:|--:|--:|--:|
| 0% | 5% | 4% | -6% | 1% |
| 50% | 52% | 54% | 38% | 34% |
| 70% | 73% | 72% | 60% | 48% |
| 90% | 92% | 90% | 85% | 77% |

Table: Calcolo risparmiato rispetto al solo modello grande, costi 1\ :\ 8\ :\ 70, accuratezza entro mezzo punto.

Come controllo di coerenza, al rapporto di costo degli studi pubblicati a due livelli (1 : 2,7) la simulazione dà dal 12% al 55% con il 70%-90% di richieste facili. Il 31% e il 43% riportati su modelli reali [2, 3] cadono in quell'intervallo. La simulazione non rivendica risultati migliori; mostra solo che i suoi numeri sono di una grandezza plausibile.

## 4.2 Quando conviene un modello intermedio

La figura 1 mostra cosa succede aggiungendo un modello intermedio, al variare del rapporto di costo fra modelli vicini da 2x a 10x.

![Punti di risparmio guadagnati o persi aggiungendo un modello intermedio a una cascata a due stadi. Linea: media su cinque quote di richieste facili (dal 50% al 90%). Fascia: dal minimo al massimo. Linea tratteggiata: 5x.](fig1_middle_model_it.pdf){width=100%}

Con un segnale buono o medio il modello intermedio è quasi inutile: su tutti i rapporti sposta il risparmio fra -24 e +4 punti, e sotto 5x non guadagna mai più di un punto circa. Con un segnale buono il modello piccolo sa già quali richieste passare avanti, quindi una fermata intermedia aggiunge costo e poco altro.

Con un segnale debole il quadro cambia. Il modello piccolo manda avanti molte richieste che non sa giudicare, e un modello intermedio ne intercetta una parte a una frazione del costo del modello grande. Il guadagno medio diventa positivo fra 3x e 4x e arriva a circa 10 punti a 10x. Da 5x in su, in queste simulazioni, il modello intermedio non perde mai più di una frazione di punto e guadagna fino a 15.

Sotto 5x, sulle tre qualità di segnale, il modello intermedio perde mezzo punto o più in 36 celle su 45 e guadagna in 6. I sei guadagni sono tutti a 3x o 4x: cinque con segnale debole, uno con segnale buono e il 90% di richieste facili.

## 4.3 Le regole come terzo stadio

La figura 2 mette uno stadio di regole accanto al modello intermedio, sulle stesse richieste.

![Punti di risparmio guadagnati o persi con un terzo stadio, rispetto a una cascata a due stadi. Linea: media su tre quote di richieste facili (50%, 70%, 90%). Fascia: dal minimo al massimo.](fig2_rules_vs_middle_it.pdf){width=100%}

Emergono due cose. La prima: lo stadio di regole è sicuro. Su tutte le 126 celle il suo risultato peggiore è una perdita di circa 3 punti, contro i 24 del modello intermedio. La seconda: quanto guadagna dipende da quanto copre e da quanto sono vicini i modelli. Con copertura al 30% e modelli a meno di 5x guadagna da 0 a 18 punti; con copertura al 10%, da -2 a +6.

Il meccanismo è semplice. Lo stadio di regole toglie le richieste facili prima che il modello piccolo le veda. Quando i modelli sono vicini nel costo, il calcolo del modello piccolo è una parte rilevante del totale, e saltarlo conta. Quando il segnale è debole, lo stadio di regole toglie anche richieste che il modello piccolo avrebbe mandato avanti per errore. Per questo i guadagni maggiori compaiono con il segnale debole: da 2 a 18 punti con copertura al 30% sotto 5x.

## 4.4 La regola del 5x

La tabella 2 riassume entrambi i confronti attorno a un'unica soglia.

| Terzo stadio | Sotto 5x | Da 5x in su |
|:--|:-:|:-:|
| Stadio di regole, copertura 30% | da 0 a +18 | da -2 a +10 |
| Stadio di regole, copertura 10% | da -2 a +6 | da -3 a +4 |
| Modello intermedio, segnale debole | da -23 a +4 | da 0 a +15 |
| Modello intermedio, segnale buono o medio | da -24 a +1 | da -6 a +4 |

Table: Intervallo del guadagno in punti di risparmio, rispetto a una cascata a due stadi.

La regola pratica che ne segue:

1. **Sotto 5x fra modelli vicini, il terzo stadio sono le regole, non un modello.** Un modello intermedio di solito costa più di quanto fa risparmiare.
2. **Da 5x in su, con segnale di fiducia debole, aggiungere un modello intermedio.** Le regole aiutano ancora se coprono abbastanza richieste.
3. **Da 5x in su, con segnale buono o medio, bastano due modelli.**
4. **Con poche richieste facili, non costruire una cascata.**

I bordi sono sfumati. Fra 3x e 4x, con segnale debole e richieste in gran parte facili, un modello intermedio guadagna già fino a 4 punti; a 5x con segnale debole e solo metà delle richieste facili va in pari. La soglia è un numero tondo scelto per essere ricordato. Ciò che i dati sostengono è la direzione: più i modelli sono vicini, meno vale un modello intermedio e più vale uno stadio di regole.

## 4.5 Profili di carico

La tabella 3 applica il planner a cinque profili illustrativi. Sono ipotesi su carichi tipici, non misure. Il planner consiglia il progetto più semplice entro 2 punti dal migliore: prima il minor numero di modelli, poi l'assenza dello stadio di regole.

| Carico (facili, copertura regole, segnale) | Costi 1 : 3 : 9 | Costi 1 : 8 : 70 |
|:-----------------------------|:---------------------|:---------------------|
| Smistamento ticket (80%, 30%, buono) | regole, piccolo, grande: 74% | piccolo, grande: 81% |
| Ricerca a catalogo (70%, 50%, buono) | regole, piccolo, grande: 67% | piccolo, grande: 72% |
| Turni di un assistente (60%, 10%, debole) | regole, piccolo, grande: 33% | regole, piccolo, medio, grande: 48% |
| Estrazione da documenti (50%, 20%, debole) | regole, piccolo, grande: 29% | piccolo, medio, grande: 39% |
| Analisi aperta (10%, 0%, debole) | solo modello grande | piccolo, grande: 5% |

Table: Progetto consigliato e relativo risparmio per cinque profili di carico illustrativi.

Con costi vicini la raccomandazione è la stessa per ogni profilo che ha richieste facili: regole davanti a due modelli. Con costi lontani dipende dal segnale, come la regola prevede.

# 5. Tenere onesta una cascata

Una cascata vale quanto la sua taratura, e la taratura decade quando il carico cambia. Due test chi quadro rendono visibile il decadimento.

**Taratura.** Si raggruppano le richieste risolte in fasce di fiducia dichiarata. Con $p_b$ la fiducia media dichiarata, $o_b$ la frequenza osservata di esiti corretti e $n_b$ il numero di casi nella fascia $b$,

$$\chi^2 = \sum_b \frac{n_b\,(o_b - p_b)^2}{p_b\,(1 - p_b)}$$

si confronta con una distribuzione chi quadro con tanti gradi di libertà quante sono le fasce. Un valore alto significa che la fiducia dichiarata non corrisponde più alla realtà e che la cascata va ritarata.

**Deriva.** Con conteggi osservati e attesi per categoria di richiesta,

$$\chi^2 = \sum_k \frac{(O_k - E_k)^2}{E_k}$$

segnala un cambiamento nella composizione delle richieste, e la parte della statistica dovuta a ogni categoria mostra dove sta il cambiamento. Per esempio, conteggi attesi di 160, 100, 100, 40 e osservati di 130, 110, 120, 40 danno 10,63, sopra il valore critico al 5% di 7,81 per tre gradi di libertà, con più della metà della statistica dovuta alla prima categoria.

Entrambi i test hanno bisogno di esiti: correzioni degli operatori, ordini confermati, regole di validazione, revisione a campione. Un carico senza dati di esito non si può tarare, e non va instradato in base alla fiducia.

# 6. Pianificare un carico di lavoro

La regola e la simulazione sono confezionate in un planner. Prende quattro numeri:

1. **La quota di richieste facili.** Si fa girare il modello più piccolo su un campione con risposte note; è la quota che risolve bene con fiducia alta.
2. **La copertura delle regole.** La quota di richieste che un passaggio deterministico risolve da solo.
3. **La scala dei costi.** Il calcolo per richiesta, misurato, di ogni modello disponibile.
4. **La qualità del segnale di fiducia.** L'area sotto la curva ROC della fiducia del modello piccolo rispetto a risposte giuste e sbagliate.

Restituisce ogni progetto con il suo risparmio simulato e consiglia il più semplice entro 2 punti dal migliore. Lo stesso planner gira nel browser come pagina unica autosufficiente, in italiano e in inglese. Il risultato è uno scenario ipotetico sotto le ipotesi della simulazione: dice a una squadra quali progetti vale la pena misurare, non quanto risparmierà un sistema reale.

# 7. Esperimenti collegati nel repository

Il repository applica la stessa logica a imbuto a un secondo problema: scegliere il migliore fra molti candidati rumorosi con un budget di valutazione fisso. I risultati principali, tutti simulati:

- Tre stadi di eliminazione portano la probabilità di scegliere il vero migliore fra 1.000 candidati dal 21% al 68% su dati rumorosi, a parità di budget. Oltre sei stadi il risultato peggiora.
- Tagliare poco all'inizio e di più dopo è la progressione robusta. Nessuna sequenza numerica nota fa meglio di una generica che cresce di circa 1,4 volte a stadio.
- Una cascata di valutatori economico, medio e preciso vince con largo margine a budget stretto (69% contro 21%) e perde contro il solo valutatore preciso a budget generoso.
- Misure di qualità diversa vanno combinate con pesi a covarianza inversa, mai con la media.

Sono risultati coerenti con la letteratura sull'eliminazione a stadi [8-12] e non sono rivendicati come nuovi.

# 8. Limiti

- **Dati sintetici.** Difficoltà, capacità e segnale di fiducia seguono ipotesi gaussiane semplici.
- **I segnali simulati sono informativi.** Anche il segnale debole ha, per il modello piccolo, un'area sotto la curva ROC fra 0,86 e 0,94. I segnali di fiducia dei modelli linguistici reali sono spesso più deboli. I confini riportati qui possono spostarsi, in un senso o nell'altro, una volta usati segnali reali.
- **Errori indipendenti.** Il rumore sulla fiducia di ogni modello è indipendente. Modelli della stessa famiglia possono sbagliare sulle stesse richieste, e questo ridurrebbe il valore del passaggio al modello successivo.
- **Uno stadio di regole idealizzato.** È accurato al 99,5% e scatta solo sulle richieste facili. Le regole reali sbagliano, e il loro valore scende di conseguenza.
- **Costi ipotizzati.** Le scale dei costi sono dati in ingresso, e regolari ($1 : r : r^2$). Le scale reali sono irregolari.
- **Una griglia di soglie grossolana.** La soglia si sceglie fra dieci valori. Una parte della variazione di un punto o due fra celle viene dalla griglia, non dai progetti.
- **La memoria non è contata.** Una cascata tiene caricati tutti i modelli. Su una sola GPU un modello più piccolo toglie memoria a quello più grande.
- **Profili illustrativi.** I carichi della tabella 3 sono ipotesi, non sistemi misurati.

# 9. Provare la regola su modelli reali

Il protocollo, nel repository, è pensato perché ogni progetto si possa valutare a posteriori con un solo passaggio sui dati:

1. Prendere tre modelli a pesi aperti di taglia nettamente diversa, serviti in locale, e un benchmark pubblico con risposte note, diviso una volta in una metà di taratura e una di prova.
2. Far girare i tre modelli una volta su ogni elemento. Salvare la risposta, se è corretta, il segnale di fiducia e il costo misurato.
3. Stimare la taratura e scegliere la soglia sulla metà di taratura.
4. Valutare ogni progetto sulla metà di prova, con intervalli di confidenza bootstrap.

I confronti sono il solo modello grande, due stadi contro tre, uno stadio di regole dove il compito lo consente, e insiemi di modelli con costi vicini e con costi lontani.

Cosa smentirebbe la regola:

- un terzo stadio, modello intermedio o regole, che non batte mai i due stadi a parità di accuratezza;
- il confine che non compare dove il rapporto di costo e la qualità del segnale dicono che dovrebbe;
- segnali di fiducia troppo deboli perché una soglia riesca a tenere l'accuratezza;
- risparmi che spariscono una volta contato il costo misurato di far girare prima i modelli più piccoli.

I risultati negativi saranno pubblicati così come sono.

# 10. Conclusioni

Le cascate a due livelli con fiducia tarata sono consolidate. Questo rapporto affronta il passo successivo: se aggiungere un terzo stadio, e quale. In simulazione la risposta dipende soprattutto da un numero, il rapporto di costo fra modelli vicini. Sotto 5x un modello intermedio di solito perde e uno stadio di regole guadagna in proporzione a quanto copre; da 5x in su un modello intermedio conviene solo quando il segnale di fiducia è debole. Spesso il terzo stadio migliore non è un modello.

È un'ipotesi con il codice allegato. I contributi più utili adesso sono un'esecuzione del protocollo su modelli reali e un caso d'uso misurato: i quattro numeri di un carico reale, e quanto la cascata ha risparmiato davvero.

# Riproducibilità

Codice, risultati e questo rapporto, in italiano e in inglese, sono su <https://github.com/gionnysimonetti-dev/calibrated-funnel> con licenza MIT. `python -m experiments.run_all` rigenera ogni numero in circa cinque minuti; i semi sono fissati per ogni cella sperimentale. Le tabelle 1-3 e le figure 1 e 2 corrispondono agli esperimenti 1, 6, 7 e 8.

# Uso di AI

Il codice delle simulazioni e parte dell'analisi statistica sono stati sviluppati con un assistente AI (Claude, Anthropic), che ha anche assistito nella stesura di questo rapporto. L'autore ha rivisto il progetto e risponde del contenuto.

# Riferimenti

1. L. Chen, M. Zaharia, J. Zou. FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance. arXiv:2305.05176, 2023.
2. V. Kotte. UCCI: Calibrated Uncertainty for Cost-Optimal LLM Cascade Routing. arXiv:2605.18796, 2026.
3. Y. Dou, S. Lian, S. Li. Conformal Cascade: Distribution-Free Accuracy Guarantees for Multi-Tier LLM Inference. arXiv:2607.25018, 2026.
4. A. Barrak, Y. Fourati, M. Olchawa, E. Ksontini, K. Zoghlami. CARGO: A Framework for Confidence-Aware Routing of Large Language Models. arXiv:2509.14899, 2025.
5. Y.-N. Chuang, P. K. Sarma, P. Gopalan, J. Boccio, S. Bolouki, X. Hu, H. Zhou. Learning to Route LLMs with Confidence Tokens. arXiv:2410.13284, 2024.
6. C. Hao, W. Lu, Y. Ishiwaka, Z. Li, W. Wan, Y. Chen. When Models Know When They Do Not Know: Calibration, Cascading, and Cleaning. arXiv:2601.07965, 2026.
7. P. Aggarwal, A. Madaan, et al. AutoMix: Automatically Mixing Language Models. arXiv:2310.12963, 2023.
8. Z. Karnin, T. Koren, O. Somekh. Almost Optimal Exploration in Multi-Armed Bandits. ICML, 2013.
9. K. Jamieson, A. Talwalkar. Non-stochastic Best Arm Identification and Hyperparameter Optimization. AISTATS, 2016.
10. S. Shahrampour, M. Noshad, V. Tarokh. On Sequential Elimination Algorithms for Best-Arm Identification in Multi-Armed Bandits. arXiv:1609.02606, 2016.
11. L. Li et al. Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization. JMLR, 2018.
12. W. G. Cochran. Improvement by means of selection. Proceedings of the Second Berkeley Symposium, 1951.
13. C. Guo et al. On Calibration of Modern Neural Networks. ICML, 2017.
14. D. W. Hosmer, S. Lemeshow. Goodness-of-fit tests for the multiple logistic regression model. Communications in Statistics, 1980.
