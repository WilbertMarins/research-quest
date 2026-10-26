const steps = [
  "Envie documentos TXT ou Markdown",
  "Faça uma pergunta sobre o conteúdo",
  "Acompanhe a pesquisa em background",
  "Receba uma resposta com as fontes",
];

export default function HomePage() {
  return (
    <main>
      <section className="hero" aria-labelledby="hero-title">
        <p className="eyebrow">MVP em construção</p>
        <h1 id="hero-title">Research Quest</h1>
        <p className="summary">
          Transforme seus documentos em respostas rastreáveis, com evidências
          claras e o estado de cada pesquisa sempre visível.
        </p>
      </section>

      <section className="workflow" aria-labelledby="workflow-title">
        <div>
          <p className="eyebrow">Fluxo principal</p>
          <h2 id="workflow-title">Da fonte à resposta</h2>
        </div>

        <ol>
          {steps.map((step, index) => (
            <li key={step}>
              <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
              {step}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
