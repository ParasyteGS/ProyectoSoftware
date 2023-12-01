#include <iostream>
#include <stdio.h>

uint8_t dato_recibido_codificadoByteLow = 0b0101100;  // 1101
uint8_t dato_recibido_codificadoByteHigh = 0b1100011; // 1100
uint8_t dato_decodificado_completo = 0;
uint8_t dato_decodificado_ByteLow = 0;
uint8_t dato_decodificado_ByteHigh = 0;

void imprimirBinario(uint8_t numero) {
  if (numero == 0) {
    printf("0");
    return;
  }

  // Encontrar el bit más significativo
  int msb = 1 << (sizeof(uint8_t) * 8 - 1);

  // Imprimir cada bit
  while (msb > 0) {
    if (numero & msb)
      printf("1");
    else
      printf("0");

    msb >>= 1;
  }
}

uint8_t extraerBit(uint8_t valor, uint8_t posicion) {
  // Crear una máscara con un 1 en la posición deseada
  uint8_t mascara = 1 << posicion;

  // Aplicar la máscara y desplazar el resultado a la posición más baja
  uint8_t bitExtraido = (valor & mascara) >> posicion;

  return bitExtraido;
}

// Función para corregir y detectar errores en el código de Hamming (7,4)
uint8_t corregirDetectarHamming74(uint8_t codigoHamming) {
  uint8_t sindrome = 0;
  uint8_t valor_decodificado = 0;

  uint8_t p1 = extraerBit(codigoHamming, 3);
  uint8_t p2 = extraerBit(codigoHamming, 1);
  uint8_t p3 = extraerBit(codigoHamming, 0);

  uint8_t d1 = extraerBit(codigoHamming, 6);
  uint8_t d2 = extraerBit(codigoHamming, 5);
  uint8_t d3 = extraerBit(codigoHamming, 4);
  uint8_t d4 = extraerBit(codigoHamming, 2);

  printf("LSB a MSB");
  printf("\n");

  printf("P3: ");
  imprimirBinario(p3);
  printf("\n");

  printf("P2: ");
  imprimirBinario(p2);
  printf("\n");

  printf("D4: ");
  imprimirBinario(d4);
  printf("\n");

  printf("P1: ");
  imprimirBinario(p1);
  printf("\n");

  printf("D3: ");
  imprimirBinario(d3);
  printf("\n");

  printf("D2: ");
  imprimirBinario(d2);
  printf("\n");

  printf("D1: ");
  imprimirBinario(d1);
  printf("\n");

  // Calcular bits de paridad
  uint8_t E1 = d1 ^ d2 ^ d4 ^ p1; // D1 D2 D3 P1 D4 P2 P3
  uint8_t E2 = d1 ^ d3 ^ d4 ^ p2; //
  uint8_t E3 = d2 ^ d3 ^ d4 ^ p3; //

  // Calcular la posición del bit de error
  sindrome = E1 | (E2 << 1) | (E3 << 2);
  printf("Sindrome: ");
  imprimirBinario(sindrome);
  printf("\n");

  // Si hay un error, corregir el bit D1 D2 D3 P1 D4 P2 P3
  if (sindrome == 3) {
    codigoHamming ^= (1 << (6)); // Corregir el bit erróneo
    printf("Error en bit 7 (D1).\n");
  }
  if (sindrome == 5) {
    codigoHamming ^= (1 << (5)); // Corregir el bit erróneo
    printf("Error en bit 6 (D2).\n");
  }
  if (sindrome == 6) {
    codigoHamming ^= (1 << (4)); // Corregir el bit erróneo
    printf("Error en bit 5 (D3).\n");
  }
  if (sindrome == 7) {
    codigoHamming ^= (1 << (2)); // Corregir el bit erróneo
    printf("Error en bit 3 (D4).\n");
  }
  if (sindrome == 0) {
    printf("No se detectaron errores.\n");
  }
  

  p1 = extraerBit(codigoHamming, 3);
  p2 = extraerBit(codigoHamming, 1);
  p3 = extraerBit(codigoHamming, 0);

  d1 = extraerBit(codigoHamming, 6);
  d2 = extraerBit(codigoHamming, 5);
  d3 = extraerBit(codigoHamming, 4);
  d4 = extraerBit(codigoHamming, 2);

  valor_decodificado = (d1 << 3) | (d2 << 2) | (d3 << 1) | d4;

  return valor_decodificado; // Devolver los 4 bits de datos corregidos
}

int main() {
  printf("Valor Low codificado: ");
  imprimirBinario(dato_recibido_codificadoByteLow);
  printf("\n");
  printf("Valor High codificado: ");
  imprimirBinario(dato_recibido_codificadoByteHigh);
  printf("\n");

  dato_decodificado_ByteLow =
      corregirDetectarHamming74(dato_recibido_codificadoByteLow);
  dato_decodificado_ByteHigh =
      corregirDetectarHamming74(dato_recibido_codificadoByteHigh);
  dato_decodificado_ByteHigh = dato_decodificado_ByteHigh << 4;

  dato_decodificado_completo =
      dato_decodificado_ByteHigh | dato_decodificado_ByteLow;

  printf("Valor Low decodificado: ");
  imprimirBinario(dato_decodificado_ByteLow);
  printf("\n");

  printf("Valor High decodificado: ");
  imprimirBinario(dato_decodificado_ByteHigh);
  printf("\n");

  printf("Valor decodificado: ");
  imprimirBinario(dato_decodificado_completo);
  printf("\n");

  return 0;
}
