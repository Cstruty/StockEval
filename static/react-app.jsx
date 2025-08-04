const { BrowserRouter, Routes, Route, Link } = ReactRouterDOM;

function NavBar() {
  return (
    <nav>
      <Link to="/">
        <svg className="nav-icon" viewBox="0 0 24 24" width="24" height="24"><path d="M12 3l10 9h-3v9h-6v-5H11v5H5v-9H2z"/></svg>
        <span>Home</span>
      </Link>
      <Link to="/OtherTools">
        <svg className="nav-icon" viewBox="0 0 24 24" width="24" height="24"><path d="M14.7 13.3l3-3c.4-.4.4-1 0-1.4l-2.6-2.6c.4-1.3.1-2.7-.9-3.7-1.5-1.5-3.9-1.8-5.7-.7L9 4.2l3 3-3 3-1.1-1.1c-1.1 1.8-.8 4.2.7 5.7 1 1 2.4 1.3 3.7.9l2.6 2.6c.4.4 1 .4 1.4 0z"/></svg>
        <span>Tools</span>
      </Link>
      <Link to="/AboutMe">
        <svg className="nav-icon" viewBox="0 0 24 24" width="24" height="24"><path d="M12 2a10 10 0 100 20 10 10 0 000-20zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
        <span>About</span>
      </Link>
    </nav>
  );
}

function Home() {
  return (
    <div className="centered-view">
      <h1>Stock Watchlist</h1>
      <p>This React front-end is under construction.</p>
    </div>
  );
}

function About() {
  return (
    <div className="about-container">
      <h1>About Me</h1>
      <div className="photo-row">
        <img src="/static/icons/skiing.jpg" alt="Skiing Photo" id="skiing-photo" />
        <img src="/static/icons/graduation.jpg" alt="Profile Photo" id="profile-photo" />
        <img src="/static/icons/fishing.jpg" alt="Fishing Photo" id="fishing-photo" />
      </div>
      <p id="about-text">
        Hello, My name is Collin Struthers. I am computer Engineer from the university of Guelph.
        My hobbies include skiing, fishing, golf, stocks (obviously), music, movies and video games. I hope you
        enjoy my website it was inspire by my favourite stock youtuber
        <a href="https://www.youtube.com/@TheCashFlowCompounder" target="_blank">The Cash Flow Computer</a>.
        If you have any suggestions on how I can improve it, please email me at
        <a href="collinstruthers@gmail.com" target="_blank">collinstruthers@gmail.com</a>
      </p>
      <div className="resume-viewer">
        <iframe src="/static/Resume.pdf" width="100%" height="900px" style={{ border: 'none', minHeight: '600px' }} title="resume">
          This browser does not support PDFs. Please download the PDF to view it:
          <a href="/static/Resume.pdf">Download PDF</a>
        </iframe>
      </div>
    </div>
  );
}

function Tools() {
  return (
    <div id="tools-container">
      <div className="tools-column">
        <h2>Brokers</h2>
        <a href="https://www.interactivebrokers.ca/" target="_blank">Interactive Broker</a>
        <br />-Good for US stocks
        <br />-Only $3 commissions
        <br />-Most extensive broker when it comes to giving you information on the stock you're looking at.
        <br />-IMPORTANT: Make sure to set your account as a cash account and not a margin account. It's a bit scammy but if you put 1000 CAD it won't automatically
        <br />convert it to USD when you buy a USD stock, it'll get you a negative USD balance and charge you interest
        <br />
        <a href="https://www.wealthsimple.com/en-ca" target="_blank">Wealthsimple</a>
        <br />-Good for everything else
        <br />-No commission fee on Canadian stocks and ETFs
        <br />-Otherwise doesn't offer much in terms of stocks but between the two you'll have everything covered.
      </div>
      <div className="tools-column">
        <h2>Other Tools</h2>
        <a href="https://finviz.com/screener.ashx?v=111" target="_blank">Finviz</a>
        <br />-For finding new stocks to buy
        <br />-Good filters to use are: Return on Investment, Insider Ownership, Debt to Equity, Current Ratio, Earnings & FCF Growth and Profitability Margins
        <br />
        <a href="https://www.tradingview.com/?utm_source=google_ads&utm_medium=cpc&utm_campaign=PPCBRAND_GOOGLE_GLOBAL_EN_SALES_BRAND&utm_id=22433085976&utm_term=tradingview&utm_content=745255148625&matchtype=e&gad_source=1&gad_campaignid=22433085976&gbraid=0AAAAABUK9i3efOYht3-QicUu3yq-GTuoy&gclid=CjwKCAjwp_LDBhBCEiwAK7Fnkl9rjZR7prK1yyFXbGYN0ghopqP8oBe-zBosLHczt9A3OuFjXLFCOBoC5AYQAvD_BwE" target="_blank">Trading View</a>
        <br />Shows similar metrics and data to Interactive Broker but I find Trading View has a better user interface and shows the most relevant information first
        <br />
        <a href="https://www.blossomsocial.com/" target="_blank">Blossom Social</a>
        <br />Basically social media but for stock traders. If there's a trader you like to follow, most likely they'll have an account here
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div id="page-background">
        <NavBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/AboutMe" element={<About />} />
          <Route path="/OtherTools" element={<Tools />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
