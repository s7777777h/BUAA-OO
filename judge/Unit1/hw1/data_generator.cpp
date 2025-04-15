#include<stdio.h>
#include<algorithm>
#include<time.h>
#include<random>
using namespace std;
int output_T=2;
int MAXN=10;
int randbetween(int l,int r){
    return (rand()*32768+rand())%(r-l+1)+l;
}
double floatRandBetween(double l,double r){
    double temp_x=randbetween(1,100000000),temp;
    temp=temp_x/100000000;
    temp*=(double)(r-l);
    temp+=l;
    return temp;
}
char infilename[20]={"data/001.in"};
FILE *inptr;
//rand_permutation
int per[200050];
void rand_permutation(int len){
    for(int i=1;i<=len;++i)    per[i]=i;
    shuffle(per+1,per+len+1,std::default_random_engine(time(NULL)));
    for(int i=1;i<=len;++i)   fprintf(inptr,"%d ",per[i]);
    fputs("",inptr);
}
int MAX_DEPTH=2;
int expected_expr_lenth=5;
int expected_term_lenth=3;
//the percentage of the positive sign
int positive_sign_percentage=50;
//the percentage of the three types of factors
int pow_percentage=35;
int signed_integer_percentage=35;
int expression_percentage=30;
//the three percentage should add up to 100
void generate_expr(int depth);
void generate_term(int depth);
void generate_factor(int depth);
void generate_signed_integer();
void generate_normal_integer(int maxval);
void generate_pow();
void generate_sign();
void set_parameter();
int main(){
    set_parameter();
    srand(time(0));
    for(int T=1;T<=output_T;++T){
        infilename[5]=T/100+'0';
        infilename[6]=(T/10)%10+'0';
        infilename[7]=T%10+'0';
        inptr=fopen(infilename,"w");
        fprintf(inptr,"0\n");
        generate_sign();
        generate_expr(0);
        fclose(inptr);
    }
    return 0;
}
void set_parameter(){
    printf("Please input the number of testcases you want to generate:\n");
    scanf("%d",&output_T);
    printf("Please input the maximum value of the depth:\n",MAX_DEPTH);
    scanf("%d",&MAX_DEPTH);
    printf("Do you want to have other costomized settings?(y/n)\n");
    char ch;
    scanf(" %c",&ch);
    if(ch=='y'){
        printf("Please input the expected length of the expression:\n");
        scanf("%d",&expected_expr_lenth);
        printf("Please input the expected length of the term:\n");
        scanf("%d",&expected_term_lenth);
        printf("Please input the percentage of positive sign:\n");
        scanf("%d",&positive_sign_percentage);
        printf("Please input the percentage of pow:\n");
        scanf("%d",&pow_percentage);
        printf("Please input the percentage of signed integer:\n");
        scanf("%d",&signed_integer_percentage);
        printf("Please input the percentage of expression:\n");
        scanf("%d",&expression_percentage);
    }
}
void generate_expr(int depth) {
    int rand_num=randbetween(1,2*expected_expr_lenth);
    for(int i=1;i<=rand_num;++i){
        generate_sign();
        generate_term(depth);
    }
}
void generate_term(int depth){
    int rand_num=randbetween(1,100);
    if(rand_num>=100/(expected_term_lenth-1)){
        generate_term(depth);
        fprintf(inptr,"*");
    }
    generate_factor(depth);    
}
void generate_factor(int depth){
    int rand_num=randbetween(1,100);
    if (rand_num<=expression_percentage){
        if(depth<MAX_DEPTH){
            fprintf(inptr,"(");
            generate_expr(depth+1);
            fprintf(inptr,")^");
            generate_normal_integer(3);
        }    
        else{
            int rand_num=randbetween(1,pow_percentage+signed_integer_percentage);
            if(rand_num<=pow_percentage){
                generate_pow();
            }
            else{
                generate_signed_integer();
            }
        }

    }
    else if(rand_num<=expression_percentage+signed_integer_percentage)    
        generate_signed_integer();
    else    generate_pow();
}
void generate_signed_integer(){
    generate_sign();
    generate_normal_integer(MAXN);
}
void generate_normal_integer(int maxval){
    int rand_num=randbetween(0,10);
    for(int i=7;i<=rand_num;++i){
        fprintf(inptr,"0");
    }
    fprintf(inptr,"%d",randbetween(0,maxval));
}
void generate_pow(){
    fprintf(inptr,"x^");
    generate_normal_integer(8);
}
void generate_sign(){
    int rand_num=randbetween(1,100);
    if(rand_num<=positive_sign_percentage)    fprintf(inptr,"+");
    else    fprintf(inptr,"-");
}