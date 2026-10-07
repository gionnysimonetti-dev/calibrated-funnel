# Calibrated Funnel Inference

**Quando conviene un terzo stadio?** Uno strumento riproducibile per progettare cascate di modelli su hardware locale, un caso d'uso alla volta.

*Read in English: [README.md](README.md)*

In una cascata risponde prima un modello piccolo, e la richiesta sale a un modello più grande solo quando una fiducia tarata resta sotto una soglia. I lavori pubblicati mostrano che con due livelli si risparmia calcolo. Questo repository si pone la domanda pratica successiva: per un dato carico di lavoro serve un terzo stadio? E quale: un modello intermedio, uno stadio di regole deterministiche, o nessuno?

**Stato: solo simulazione.** Ogni numero qui viene da dati sintetici. Nessun modello reale è stato ancora eseguito. Il protocollo per i modelli reali è in [docs/REAL_MODEL_PROTOCOL.md](docs/REAL_MODEL_PROTOCOL.md), e chi vuole aiutare a eseguirlo è benvenuto.

**Paper (bozza).** [La regola del 5x: come scegliere il terzo stadio di una cascata di modelli governata dalla fiducia](paper/paper.it.pdf), anche [in inglese](paper/paper.pdf).

## La risposta breve: la regola del 5x (simulata)

Si prende il rapporto di costo fra modelli vicini: dal piccolo al medio, dal medio al grande.

| Situazione | Terzo stadio | Effetto sul calcolo risparmiato, rispetto a due modelli |
| --- | --- | --- |
| Sotto 5x | Regole, non un modello | Regole che risolvono il 30% delle richieste: da 0 a +18 punti. Un modello intermedio perde in 36 carichi simulati su 45, fino a 24 punti |
| Da 5x in su, segnale di fiducia debole | Un modello intermedio | Da 0 a +15 punti. Le regole aggiungono ancora da 1 a 10 punti con copertura al 30% |
| Da 5x in su, segnale di fiducia buono o medio | Nessuno | Un modello intermedio sposta il risparmio fra -6 e +4 punti |
| Poche richieste facili | Nessuna cascata | Il solo modello grande costa uguale o meno |

Spesso il terzo stadio migliore non è un modello. In queste simulazioni uno stadio di regole deterministiche (codici esatti, ricerche in tabella, regole fisse) non è mai costato più di 3 punti; un modello intermedio fino a 24. Quanto guadagnano le regole dipende da quanto coprono: con copertura al 10% il guadagno è piccolo, fra -2 e +6 punti sotto 5x.

È una regola pratica ricavata da carichi simulati (esperimento 8), e i suoi bordi sono sfumati: fra 3x e 4x, con segnale debole e richieste in gran parte facili, un modello intermedio guadagna già fino a 4 punti. È l'affermazione che questo repository vuole più di tutte vedere provata su modelli reali.

Il risparmio in sé lo decide il carico di lavoro, non il metodo: contano soprattutto la quota di richieste facili e il rapporto di costo fra i modelli.

## Pianifica il tuo carico di lavoro

**Nel browser.** Apri [calculator/index.html](calculator/index.html): quattro numeri in ingresso, in uscita il progetto che vale la pena provare. Nessuna installazione e nessun server, in italiano e in inglese. È una trasposizione in JavaScript del planner qui sotto; su otto profili di prova dà la stessa raccomandazione, con risparmi entro 2 punti.

**Da riga di comando.**

```bash
python -m funnel.planner --easy 0.6 --rules 0.1 --costs 1 3 9 --signal weak
```

```
design                                   saving   accuracy
rules > small > large                       33%      -0.4
small > large                               28%      -0.3
rules > small > medium > large              26%      -0.4
small > medium > large                      21%      -0.3
rules > large model only                    10%      -0.0

simplest design within 2 points of the best: rules > small > large
```

`--easy` è la quota di richieste facili, `--rules` la quota che un primo stadio deterministico risolve da solo, `--costs` il calcolo relativo del modello piccolo, medio e grande, `--signal` la qualità del segnale di fiducia (`good`, `medium` o `weak`). Il risultato è uno scenario ipotetico sotto le ipotesi della simulazione: dice quali progetti vale la pena misurare, non quanto risparmierà un sistema reale.

## Casi d'uso

[docs/USE_CASES.md](docs/USE_CASES.md) descrive dove una cascata tende a funzionare e dove no: smistamento dei ticket in una tassonomia fissa, ricerca a catalogo e di ricambi, turni di un assistente commerciale o di supporto, estrazione di campi da documenti. Per ciascuno: quali sono in pratica gli stadi, da dove arrivano gli esiti per la taratura, quanto costa un errore e cosa misurare per primo.

La documentazione di dettaglio nella cartella `docs/` è in inglese.

## Cosa è, e cosa non è

Le cascate governate dalla fiducia non sono nuove, nemmeno con fiducia tarata e su modelli aperti serviti in locale (vedi [Lavori correlati](#lavori-correlati)). Questo repository non rivendica l'idea. Il metodo è stato raggiunto in modo indipendente e poi confrontato con la letteratura.

Cosa aggiunge:

- **La regola del 5x**: una regola di decisione per il terzo stadio, in base alla scala dei costi, alla qualità della fiducia e al carico di lavoro.
- **Lo stadio di regole deterministiche come stadio a pieno titolo**: ricerche esatte e regole fisse risolvono ciò che possono prima che giri un modello.
- **Un planner** che trasforma quattro numeri misurabili in una rosa di progetti da provare, da riga di comando o nel browser.
- **Verifica continua**: test chi quadro che dicono quando la taratura è andata fuori e quando è cambiata la composizione delle richieste.
- **Codice che riproduce ogni numero** con un comando, così le affermazioni si possono controllare, smentire o migliorare.

## Il metodo in cinque passi

1. Tre stadi con valutatori diversi, dal più economico al più preciso.
2. A ogni stadio, un taglio proporzionato all'affidabilità del valutatore di quello stadio.
3. Una scelta finale che combina le misure usando la loro covarianza.
4. Una statistica chi quadro come grado di fiducia.
5. Taratura di quella fiducia sugli esiti reali, verificata con un altro test chi quadro.

Formule e ipotesi sono in [docs/METHOD.md](docs/METHOD.md).

## Risultati (simulati)

Le tabelle complete sono in [results/RESULTS.md](results/RESULTS.md); ognuna ha accanto il suo CSV.

### Calcolo risparmiato a parità di accuratezza

Costi relativi dei modelli 1 : 8 : 70. L'accuratezza resta entro mezzo punto dal solo modello più grande. La soglia si sceglie su un campione di taratura e i risultati si misurano su un campione di prova separato di 300.000 richieste.

| Richieste facili | Segnale buono, 3 stadi | Segnale buono, 2 stadi | Segnale debole, 3 stadi | Segnale debole, 2 stadi |
| --- | --- | --- | --- | --- |
| 0% | 5% | 4% | -6% | 1% |
| 50% | 52% | 54% | 38% | 34% |
| 70% | 73% | 72% | 60% | 48% |
| 90% | 92% | 90% | 85% | 77% |

Il risparmio riguarda calcolo, energia e latenza, non la memoria: tutti i modelli devono restare caricati.

### Il valore del modello intermedio

Punti di risparmio guadagnati o persi aggiungendo il modello intermedio, con segnale di fiducia debole.

| Costi dei modelli | 50% di richieste facili | 70% di richieste facili | 90% di richieste facili |
| --- | --- | --- | --- |
| 1 : 1,7 : 3 | -21 | -16 | -3 |
| 1 : 3 : 9 | -10 | 0 | +3 |
| 1 : 5 : 25 | 0 | +12 | +7 |
| 1 : 8 : 70 | +5 | +12 | +9 |

Con un segnale buono il modello intermedio guadagna al massimo 2 punti e ne perde fino a 23 quando i costi sono vicini.

L'esperimento 8 fa variare il rapporto fra modelli vicini da 2x a 10x, con tre qualità di segnale, e confronta uno stadio di regole con un modello intermedio come terzo stadio. La regola del 5x viene da lì.

### Controllo di coerenza con i risultati pubblicati

Al rapporto di costo usato negli studi pubblicati a due livelli (1 : 2,7), questa simulazione dà un risparmio fra il 12% e il 55% con il 70%-90% di richieste facili. Due studi su modelli reali riportano il 31% e il 43%. La simulazione sta nello stesso intervallo e non rivendica risultati migliori.

### Eliminazione a stadi fra candidati rumorosi

La stessa logica a imbuto vale per scegliere il migliore fra molti candidati con un budget di valutazione fisso: varianti di prompt, configurazioni, scenari di intervento. 1.000 candidati, 16 valutazioni per candidato in totale, probabilità di scegliere quello davvero migliore.

| Progetto | Dati puliti | Dati rumorosi |
| --- | --- | --- |
| Nessuna eliminazione | 61% | 21% |
| Tre stadi, coefficienti uguali | 95% | 68% |
| Tre stadi, coefficienti crescenti di 1,62 volte | 95% | 74% |
| Tre stadi, coefficienti decrescenti (0,62 volte) | 95% | 60% |
| Tre stadi, crescita 1,4 volte, budget in parti uguali | 96% | 71% |
| Tre stadi, crescita 1,4 volte, al primo stadio il 10% del budget | 93% | 47% |

- Il grosso del guadagno viene dal passare da uno stadio a tre. Oltre sei stadi il risultato peggiora.
- Con dati rumorosi, tagliare poco all'inizio e di più dopo.
- Non lasciare a secco il primo stadio.

### Cascata di valutatori di costo diverso

1.000 candidati, costi dei valutatori 1 : 5 : 25. Budget 1 equivale a una valutazione precisa di ogni candidato.

| Budget | Solo valutatore preciso, tre stadi | Cascata economico, medio, preciso |
| --- | --- | --- |
| 0,25 | 6% | 37% |
| 1 | 21% | 69% |
| 2 | 45% | 77% |
| 4 | 87% | 82% |

Con un budget stretto la cascata vince con largo margine. Con un budget generoso il solo valutatore preciso recupera, perché gli errori sistematici del valutatore economico a volte scartano per sempre il candidato migliore. Più il primo valutatore è affidabile, più forte può tagliare: il taglio migliore al primo stadio tiene il 33% dei candidati con affidabilità 0,4, il 12% con 0,8 e il 2% con 0,95.

### Combinare le misure e fidarsi del risultato

- **Mai fare la media di misure di qualità diversa.** La media semplice delle tre perde fino a 20 punti rispetto alla sola ultima misura. Pesare con l'inverso della covarianza guadagna da 0,4 a 4 punti.
- **Un chi quadro sullo scarto fra i due candidati in testa ordina bene i casi**: la scelta è corretta nell'87% del quinto più sicuro e nel 36% del quinto meno sicuro. Letto così com'è, non è una probabilità.
- **La probabilità a posteriori del modello di covarianza è tarata**: frequenze dichiarate e osservate coincidono fascia per fascia, e supera il test chi quadro di taratura (7,5 su 9 fasce, p = 0,59).

## Cosa non regge

Cose provate che non hanno retto:

- Un insieme universale di coefficienti di riduzione. I migliori dipendono dal numero di candidati e dal rumore.
- Un ruolo speciale di numeri primi, numeri di Fibonacci o altre sequenze note. Una progressione generica che cresce di 1,4 volte a stadio eguaglia o batte ogni sequenza nota provata (esperimento 5).
- Un terzo modello come miglioramento generale. Aiuta in un angolo dello spazio e danneggia altrove (esperimenti 6 e 8).
- Soglie fisse di evidenza nello stile di un test sequenziale del rapporto di verosimiglianza. In prove preliminari, non incluse qui, non hanno battuto le frazioni fisse a budget fisso.

## Riprodurre

```bash
pip install -r requirements.txt
python -m pytest -q                 # circa due secondi
python -m experiments.run_all       # circa cinque minuti, riscrive results/
```

I semi sono fissati per ogni cella sperimentale: con le stesse versioni delle librerie il risultato è identico a ogni esecuzione.

## Struttura del repository

```
funnel/routing.py       cascata di modelli governata dalla fiducia, con stadio di regole opzionale
funnel/planner.py       planner di scenari per un profilo di carico
calculator/index.html   il planner nel browser, in italiano e in inglese
funnel/selection.py     eliminazione a stadi, con un valutatore e con una cascata di valutatori
funnel/confidence.py    pesi di covarianza, fiducia chi quadro, test di taratura e di deriva
experiments/            uno script per esperimento, più run_all
results/                RESULTS.md e un CSV per tabella
docs/                   metodo, casi d'uso, protocollo per modelli reali, questioni aperte
paper/                  rapporto tecnico, in italiano e in inglese, con le figure
realtest/               primo test su modelli reali: script, risultati salvati, rapporto
tests/                  test unitari
```

## Limiti

- **Dati sintetici.** Difficoltà, capacità dei modelli e segnale di fiducia seguono ipotesi gaussiane semplici. I modelli reali possono comportarsi diversamente, soprattutto su quanto è informativo il loro segnale di fiducia.
- **Profili di carico illustrativi.** I profili dei casi d'uso sono ipotesi, non misure di sistemi reali.
- **Costi ipotizzati.** Le scale dei costi sono dati in ingresso. Vanno misurate sul proprio hardware.
- **Indipendenza ottimistica.** Nella simulazione il rumore sulla fiducia di ogni modello è indipendente. Modelli della stessa famiglia possono sbagliare sulle stesse richieste.
- **Uno stadio di regole idealizzato.** Si assume accurato al 99,5% su ciò che risolve e attivo solo sulle richieste facili.

## Lavori correlati

Cascate e instradamento di modelli:

- Chen, Zaharia, Zou. [FrugalGPT](https://arxiv.org/abs/2305.05176), 2023.
- Kotte. [UCCI: Calibrated Uncertainty for Cost-Optimal LLM Cascade Routing](https://arxiv.org/abs/2605.18796), 2026. Due modelli serviti in locale, taratura isotonica, riduzione dei costi del 31%.
- Dou, Lian, Li. [Conformal Cascade: Distribution-Free Accuracy Guarantees for Multi-Tier LLM Inference](https://arxiv.org/abs/2607.25018), 2026. Schema a più livelli con garanzie formali di accuratezza, valutato con due livelli su modelli a pesi aperti, riduzione dei costi del 43%.
- Barrak, Fourati, Olchawa, Ksontini, Zoghlami. [CARGO: A Framework for Confidence-Aware Routing of Large Language Models](https://arxiv.org/abs/2509.14899), 2025.
- Chuang, Sarma, Gopalan, Boccio, Bolouki, Hu, Zhou. [Learning to Route LLMs with Confidence Tokens](https://arxiv.org/abs/2410.13284), 2024.
- Hao, Lu, Ishiwaka, Li, Wan, Chen. [When Models Know When They Do Not Know: Calibration, Cascading, and Cleaning](https://arxiv.org/abs/2601.07965), 2026.
- Aggarwal, Madaan, et al. [AutoMix: Automatically Mixing Language Models](https://arxiv.org/abs/2310.12963), 2023.

Eliminazione a stadi con budget fisso:

- Karnin, Koren, Somekh. [Almost Optimal Exploration in Multi-Armed Bandits](https://proceedings.mlr.press/v28/karnin13.pdf) (Sequential Halving), 2013.
- Jamieson, Talwalkar. [Non-stochastic Best Arm Identification and Hyperparameter Optimization](https://arxiv.org/abs/1502.07943), 2016.
- Shahrampour, Noshad, Tarokh. [On Sequential Elimination Algorithms for Best-Arm Identification in Multi-Armed Bandits](https://arxiv.org/abs/1609.02606), 2016.
- Li e coautori. [Hyperband](https://homes.cs.washington.edu/~jamieson/hyperband.html), 2018.
- Cochran. Improvement by means of selection, 1951.

Statistica:

- Guo e coautori. [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), 2017.
- Hosmer, Lemeshow. Goodness-of-fit tests for the multiple logistic regression model, 1980.
- Wald. Sequential tests of statistical hypotheses, 1945.
- Mahalanobis. On the generalised distance in statistics, 1936.

La verifica della letteratura è parziale. Segnalazioni di lavori che mancano in questo elenco sono benvenute.

## Contribuire

I contributi più utili sono un'esecuzione del protocollo su modelli reali e un caso d'uso misurato: i quattro numeri di un carico reale e quanto la cascata ha risparmiato davvero. I controesempi sono altrettanto benvenuti. Vedi [CONTRIBUTING.md](CONTRIBUTING.md) e [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md).

## Uso di AI

Il codice delle simulazioni e parte dell'analisi statistica sono stati sviluppati con un assistente AI (Claude, Anthropic). L'autore ha rivisto il progetto e risponde del contenuto. Tutti i risultati si possono rigenerare da questo repository.

## Licenza e citazione

Codice con licenza MIT. Per citare questo lavoro vedi [CITATION.cff](CITATION.cff).

Autore: Giovanni Simonetti.
