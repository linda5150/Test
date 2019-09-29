#define _GNU_SOURCE

#include <fcntl.h>			//Needed for SPI port
#include <sys/ioctl.h>			//Needed for SPI port
#include <linux/spi/spidev.h>		//Needed for SPI port
#include <stdio.h>
#include <time.h>
#include <stdlib.h>
#include <string.h>
#include <bcm2835.h>

#define MAX_LENTH_OF_LINE 1024

#define PIN_GPIO RPI_V2_GPIO_P1_12	
#define PIN_RESET RPI_V2_GPIO_P1_11
#define OFFSET_GPIO 0
#define OFFSET_RESET 1

#define PIN1 2
#define PIN2 3
#define PIN3 4
#define Rst_n 25
#define FPGA_State 14
#define FPGA_Read_INT 23

const char *config_data_txt = "/home/pi/testbed/testbed_data/cfg.txt";
const char *original_data_txt_addr = "/home/pi/testbed/testbed_data/";
const char *original_data_txt_name = "FPGA";
const char *original_data_txt_file_type = ".csv";
//*******************************************
//*******************************************
//****************** main *******************
//*******************************************
//*******************************************

int SetPositionByLine(FILE *fp, int nLine)
{
	int i=0;
	char buffer[MAX_LENTH_OF_LINE + 1];
	fpos_t pos;
	
	rewind(fp);
	for(;i < nLine ; i++)
		fgets(buffer,MAX_LENTH_OF_LINE,fp);
	fgetpos(fp,&pos);
	return 0;
}

time_t t,t_temp;
struct tm*lt;
char str_txt[64];
int main(int argc, char* argv){

	if (!bcm2835_init())
		return -5;
	bcm2835_spi_begin();
	bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);
	bcm2835_spi_setDataMode(BCM2835_SPI_MODE3);
	bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_64);
	bcm2835_spi_chipSelect(BCM2835_SPI_CS1);
	bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS1, LOW);

	bcm2835_gpio_fen(PIN_RESET);

	unsigned char tx_data[] = { 0xaa, 0x00, 0x01,0x00 ,0x00}; 
	unsigned char rx_data[sizeof(tx_data)] = { 0x00 }; 
	unsigned char buf[sizeof(rx_data)-2+sizeof(struct timespec)+sizeof(uint8_t)]={0};

	unsigned char txd[13] = {0x55}; 
	unsigned char rxd[13] = {0}; 

	bcm2835_gpio_fsel(PIN1,BCM2835_GPIO_FSEL_OUTP);
	bcm2835_gpio_fsel(PIN2,BCM2835_GPIO_FSEL_OUTP);
	bcm2835_gpio_fsel(PIN3,BCM2835_GPIO_FSEL_OUTP);
	bcm2835_gpio_fsel(Rst_n,BCM2835_GPIO_FSEL_OUTP);
	bcm2835_gpio_fsel(FPGA_State,BCM2835_GPIO_FSEL_INPT);
	bcm2835_gpio_fsel(FPGA_Read_INT,BCM2835_GPIO_FSEL_INPT);
	bcm2835_gpio_write(PIN1,HIGH);
	bcm2835_gpio_write(PIN2,HIGH);
	bcm2835_gpio_write(PIN3,HIGH);
	bcm2835_gpio_write(Rst_n,HIGH);
	
	unsigned int run_time,file_row,flag,count,num;
	char buffer[MAX_LENTH_OF_LINE+1];
	
	char serial_num[MAX_LENTH_OF_LINE+1];
	
	int IP_num,channel_num;
	int file_num = 0;
	int k=0;
	
	while(1)
	{
		FILE *fpRead = fopen(config_data_txt,"r+");
		if(fpRead != NULL)
		{
			file_row = 0;			
			while((flag = fgetc(fpRead)) != EOF)
			{	
				if(flag == '\n')
					file_row++;
			}
			//printf("%d\n",file_row);
			SetPositionByLine(fpRead,file_row-3);
			fgets(buffer,MAX_LENTH_OF_LINE,fpRead);
			if(buffer[0] == ';')
			{
				for(count = 0;count<file_row-3;count++)
				{
					SetPositionByLine(fpRead,count);
					fgets(buffer,MAX_LENTH_OF_LINE,fpRead);
					num = atoi(buffer);
					switch(count)
					{
						case 0:run_time = num;printf("%d\n",num);break;
						case 1://printf("%x",buffer[27]);
								while(buffer[k] != 0x0a)
								{
									serial_num[k]=buffer[k];
									printf("%c",serial_num[k]);
									k++;								
								}
								serial_num[k]=0;
								printf("%d\n",k);
								break;
						case 2:IP_num = num;printf("%d\n",num);break;
						case 3:channel_num = num;printf("%d\n",num);break;
						default:break;
					}
				}
				SetPositionByLine(fpRead,file_row-3);
				fprintf(fpRead," ");
				fgets(buffer,MAX_LENTH_OF_LINE,fpRead);
				printf("%s",buffer);
				fclose(fpRead);
				break;
			}
			fclose(fpRead);	
			bcm2835_delay(500);
		}
		else
		{
			fclose(fpRead);	
			bcm2835_delay(500);
		}
	}
	
	unsigned int i,j;
	printf("Send run time!\n");
	tx_data[1]=run_time >> 8;
	tx_data[2]=run_time & 0x00ff;
	
	bcm2835_spi_transfernb(tx_data,rx_data,sizeof(tx_data));
	printf("Recived:%x,%x,%x,%x,%x\r\n",rx_data[0],rx_data[1],rx_data[2],rx_data[3],rx_data[4]);
	bcm2835_delay(500);
	bcm2835_gpio_write(Rst_n,LOW);
	bcm2835_delay(500);
	bcm2835_gpio_write(Rst_n,HIGH);
	bcm2835_delay(500);
	while(!bcm2835_gpio_lev(FPGA_State));
	printf("FPGA IS RUNNING!\r\n");
	
	j=0;
	time(&t);
	t_temp=t;
	//printf("%d/%d/%d %d:%d:%d\n",lt->tm_year+1900,lt->tm_mon,lt->tm_mday,lt->tm_hour,lt->tm_min,lt->tm_sec);
	sprintf(str_txt,"%s%s_%d_%d_%s%d%s",original_data_txt_addr,serial_num,IP_num,channel_num,original_data_txt_name,file_num,original_data_txt_file_type);
	printf("%s\n",str_txt);
	
	FILE *fp=fopen(str_txt,"w");
	//return 0;
	if(fp==NULL)
	{
		printf("file open failed!\r\n");
		return 0;
	}
	while(bcm2835_gpio_lev(FPGA_State)) 
	{
		if(bcm2835_gpio_lev(FPGA_Read_INT))
		{
			for(i=0;i<20;i++)
			{
				bcm2835_spi_transfernb(txd,rxd,13);
			//printf("copy that\r\n");
				fprintf(fp,"%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x,\r\n",\
						rxd[12],rxd[11],rxd[10],rxd[9],rxd[8],rxd[7],\
						rxd[6],rxd[5],rxd[4],rxd[3],rxd[2],rxd[1]);
				bcm2835_delayMicroseconds(1);
			}
			j++;
			printf("%d\r\n",j);
		}
		time(&t);
		if(t-t_temp>=60*5)
		{
			t_temp=t;
			file_num++;
			fclose(fp);
			sprintf(str_txt,"%s%s_%d_%d_%s%d%s",original_data_txt_addr,serial_num,IP_num,channel_num,original_data_txt_name,file_num,original_data_txt_file_type);
			printf("%s\n",str_txt);
			fp=fopen(str_txt,"w");
			if(fp==NULL)
			{
				printf("file open failed!\r\n");
				return 0;
			}
		}
		//bcm2835_delayMicroseconds(20);
		
	}
	fclose(fp);
	printf("FPGA HAS STOPPED!\r\n");
	bcm2835_spi_end();
	bcm2835_close();

}
