import type { Metadata } from "next";

type Player = { name: string; club: string; shirt: string };
type SquadRow = { label: string; players: Player[] };

const squad: SquadRow[] = [
  { label: "Goalkeepers", players: [{ name: "Lammens", club: "Man Utd", shirt: "united" }, { name: "Ellborg", club: "Sunderland", shirt: "sunderland" }] },
  { label: "Defenders", players: [{ name: "Mazraoui", club: "Man Utd", shirt: "united" }, { name: "Yoro", club: "Man Utd", shirt: "united" }, { name: "Davies", club: "Spurs", shirt: "spurs" }, { name: "Sessegnon", club: "Fulham", shirt: "fulham" }, { name: "Canvot", club: "Crystal Palace", shirt: "palace" }] },
  { label: "Midfielders", players: [{ name: "Dasilva", club: "Brentford", shirt: "brentford" }, { name: "Nyoni", club: "Liverpool", shirt: "liverpool" }, { name: "Nelson", club: "Arsenal", shirt: "arsenal" }, { name: "Maddison", club: "Spurs", shirt: "spurs" }, { name: "Dowman", club: "Arsenal", shirt: "arsenal" }] },
  { label: "Forwards", players: [{ name: "Haaland", club: "Man City", shirt: "city" }, { name: "Kostoulas", club: "Brighton", shirt: "brighton" }, { name: "Awoniyi", club: "Coventry City", shirt: "coventry" }] },
];

export const metadata: Metadata = { title: "Selected XV | FPL Model", description: "The current optimised 15-player FPL squad." };

function Shirt({ player }: { player: Player }) {
  return <span className={`shirt shirt--${player.shirt}`} aria-hidden="true"><span className="shirt__collar" /></span>;
}

export default function Home() {
  return <main className="page-shell"><section className="pitch" aria-labelledby="squad-title">
    <header className="pitch__header"><p className="eyebrow">FPL MODEL / CURRENT SELECTION</p><h1 id="squad-title">Selected <em>XV</em></h1><p className="subtitle">Optimised 15-player squad</p></header>
    <div className="pitch__markings" aria-hidden="true"><span className="halfway-line" /><span className="centre-circle" /><span className="penalty-box penalty-box--top" /><span className="penalty-box penalty-box--bottom" /></div>
    <div className="squad" aria-label="Selected fifteen-player squad">{squad.map((row) => <section className="position-row" key={row.label} aria-label={row.label}><p className="position-label">{row.label}</p><div className={`players players--${row.players.length}`}>{row.players.map((player) => <article className="player" key={`${player.name}-${player.club}`}><Shirt player={player} /><div className="player__details"><h2>{player.name}</h2><p>{player.club}</p></div></article>)}</div></section>)}</div>
    <footer className="pitch__footer"><span>15 players</span><span className="footer-dot" /><span>£86.5m squad value</span><span className="footer-dot" /><span>114.0 projected points</span></footer>
  </section></main>;
}
