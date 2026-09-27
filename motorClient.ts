/**
 * Cliente do motor de nesting externo (Cloud Run).
 *
 * Substitui `empacotarMaterial()` do nestingEngine.ts local.
 * O que continua no Node: conversão de unidades, dedução de fita,
 * agrupamento por material. O que sai: toda a geometria.
 */

const MOTOR_URL = process.env.MOTOR_URL ?? '';
const MOTOR_TOKEN = process.env.MOTOR_API_TOKEN ?? '';

export interface PecaParaMotor {
  id: string;
  instanceId: string;
  largura: number; // mm, já com fita deduzida
  altura: number;
}

export interface RetanguloChapa {
  pecaId: string;
  instanceId: string;
  x: number;
  y: number;
  w: number;
  h: number;
  rotated: boolean;
}

export interface Retalho {
  x: number;
  y: number;
  w: number;
  h: number;
  largura: number;
  comprimento: number;
  aproveitavel: boolean;
  areaM2: number;
}

export interface Corte {
  ordem: number;
  estagio: 1 | 2;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface ChapaResultado {
  numero: number;
  larguraChapa: number;
  comprimentoChapa: number;
  refiloMm: number;
  pecas: RetanguloChapa[];
  retalhos: Retalho[];
  sequenciaCortes: Corte[];
  areaUtilizadaMm2: number;
  areaTotalMm2: number;
  areaRetalhosMm2: number;
  perdaMm2: number;
  aproveitamentoPercentual: number;
}

export interface RespostaMotor {
  chapas: ChapaResultado[];
  totalChapasUtilizadas: number;
  validacao: {
    ok: boolean;
    porChapa: Array<{
      dentroDosLimites: boolean;
      semSobreposicao: boolean;
      guilhotinavel: boolean | null;
      todasPecasAlocadas: boolean;
    }>;
    pecasEsperadas: number;
    pecasAlocadas: number;
  };
  solverStatus: string;
  tempoMs: number;
}

export interface OpcoesMotor {
  larguraChapa: number;
  alturaChapa: number;
  refiloMm: number;
  kerfMm: number;
  retalhoMinimoMm: number;
  permiteRotacao: boolean; // false quando material.temVeio
  tempoLimiteS?: number;
}

export async function empacotarViaMotor(
  pecas: PecaParaMotor[],
  opcoes: OpcoesMotor,
): Promise<RespostaMotor> {
  if (!MOTOR_URL) {
    throw new Error('MOTOR_URL não configurada — defina o endereço do Cloud Run.');
  }

  const body = {
    chapa: {
      largura: opcoes.larguraChapa,
      altura: opcoes.alturaChapa,
      refiloMm: opcoes.refiloMm,
    },
    pecas,
    kerfMm: opcoes.kerfMm,
    retalhoMinimoMm: opcoes.retalhoMinimoMm,
    permiteRotacao: opcoes.permiteRotacao,
    tempoLimiteS: opcoes.tempoLimiteS ?? 5,
  };

  // Cloud Run com cold start pode demorar; timeout generoso mas finito.
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 90_000);

  try {
    const resp = await fetch(`${MOTOR_URL}/otimizar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(MOTOR_TOKEN ? { Authorization: `Bearer ${MOTOR_TOKEN}` } : {}),
      },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });

    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`Motor retornou ${resp.status}: ${txt}`);
    }

    const dados = (await resp.json()) as RespostaMotor;

    // Nunca aceitar plano inválido — melhor falhar do que cortar errado.
    if (!dados.validacao.ok) {
      throw new Error(
        `Motor devolveu plano inválido (${dados.validacao.pecasAlocadas}/${dados.validacao.pecasEsperadas} peças alocadas).`,
      );
    }

    return dados;
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Motor de corte não respondeu a tempo. Tente novamente.');
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
