#include<stdio.h>
#include<algorithm>
#include<time.h>
#include<random>
using namespace std;
int output_T=2;
int MAXN=10;
int randbetween(int l,int r){
    if (l>r)    return 0;
    return (rand()*32768+rand())%(r-l+1)+l;
}
bool rand_boolean(int chance){
    return randbetween(1,100)<=chance;
}
char infilename[20]={"data/0001.in"};
FILE *inptr;
//rand_permutation
int per[200050];
void rand_permutation(int len){
    for(int i=1;i<=len;++i)    per[i]=i;
    shuffle(per+1,per+len+1,std::default_random_engine(time(NULL)));
    for(int i=1;i<=len;++i)   fprintf(inptr,"%d ",per[i]);
    fputs("",inptr);
}
int function_type;
bool enable_function_f;
bool enable_multi_variables;
bool enable_function_g;
bool enable_derivation;
int g_function_type;
bool enable_function_h;
int h_function_type;
/***************
function_type = 0: no function
function_type = 1: f(x)
function_type = 2: f(y)
function_type = 3: f(x,y)
function_type = 4: f(y,x)
***************/
int MAX_DEPTH=3;
int expected_expr_lenth=2;
int expected_term_lenth=1;
int pow_max=3;
//the percentage of the positive sign
int positive_sign_percentage=50;
//the percentage of the three types of factors
int function_percentage=10;
int pow_percentage=25;
int signed_integer_percentage=20;
int expression_percentage=15;
int triFunction_percentage=15;
int derivation_percentage=15;
//the three percentage should add up to 100
int expr_pow_percentage=50;
void generate_expr(int depth);
void generate_term(int depth);
void generate_factor(int depth);
void generate_signed_integer();
void generate_derivation(int depth);
void generate_normal_integer(int maxval);
void generate_function_gh();//generate the list of function of g,h
void generate_g();
void generate_h();
void generate_pow();
void generate_sign();
void generate_triFunction(int depth);
void generate_function(int depth);
void set_parameter();
void set_infilename(int num);
void generate_function_list();
void generate_regular_function(int num);
void print_function_type(int ft);
void generate_functionf(int depth);//generate the factor of function f
void generate_functiong(int depth);
void generate_functionh(int depth);
void generate_some_function();
int main(){
    set_parameter();
    srand(time(0));
    for(int T=1;T<=output_T;++T){
        set_infilename(T);
        inptr=fopen(infilename,"w");
        enable_derivation = false;
        enable_function_f = false;
        enable_multi_variables = true;
        generate_function_gh();
        if(rand_boolean(50)){
            fprintf(inptr,"1\n");
            function_type = randbetween(1,4);
            generate_function_list();
            enable_function_f = true;
        }
        else{
            fprintf(inptr,"0\n");
            function_type = 0;
        }            
        enable_multi_variables = false;
        enable_derivation = true;
        generate_expr(1);       
        if(rand_boolean(90)){
            generate_some_function();
        }
        fclose(inptr);
    }
    return 0;
}
void generate_some_function(){
    if (enable_function_f) {
        fprintf(inptr,"+");
        generate_functionf(2);

    }
    if (enable_function_g) {
        fprintf(inptr,"+");
        generate_functiong(2);

    }
    if (enable_function_h) {
        fprintf(inptr,"+");
        generate_functionh(2);
    }
}
void generate_function_gh() {
    int rand_num = randbetween(1,5);
    enable_function_g = false;
    enable_function_h = false;
    if(rand_num == 1) {
        fprintf(inptr,"0\n");
    }
    else if(rand_num == 2) {
        fprintf(inptr,"1\n");
        g_function_type = randbetween(1,4);
        generate_g();
        enable_function_g = true;
    }
    else if(rand_num == 3) {
        fprintf(inptr,"1\n");
        h_function_type = randbetween(1,4);
        generate_h();
        enable_function_h = true;
    }
    else if(rand_num == 4) {
        fprintf(inptr,"2\n");
        g_function_type = randbetween(1,4);
        h_function_type = randbetween(1,4);
        generate_g();
        enable_function_g = true;
        generate_h();
        enable_function_h = true;
    }
    else {
        fprintf(inptr,"2\n");
        h_function_type = randbetween(1,4);
        g_function_type = randbetween(1,4);
        generate_h();
        enable_function_h = true;
        generate_g();
        enable_function_g = true;
    }
}
void generate_g(){
    fprintf(inptr,"g");
    print_function_type(g_function_type);
    fprintf(inptr,"=");
    function_type = g_function_type;
    generate_expr(1);
    fprintf(inptr,"\n");
}
void generate_h(){
    fprintf(inptr,"h");
    print_function_type(h_function_type);
    fprintf(inptr,"=");
    function_type = h_function_type;
    generate_expr(1);
    fprintf(inptr,"\n");
}
void generate_derivation(int depth) {
    fprintf(inptr,"dx(");
    generate_expr(depth+1);
    fprintf(inptr,")");
}
void print_function_type(int ft){
    if(ft == 1){
        fprintf(inptr,"(x)");
    }
    else if(ft == 2){
        fprintf(inptr,"(y)");
    }
    else if(ft == 3){
        fprintf(inptr,"(x,y)");
    }
    else if(ft == 4){
        fprintf(inptr,"(y,x)");
    }
}
void generate_regular_function(int num){
    fprintf(inptr,"f{%d}",num);
    print_function_type(function_type);
    fprintf(inptr,"=");
    generate_expr(1);
    fprintf(inptr,"\n");
}
void generate_function_list() {
    generate_regular_function(0);
    generate_regular_function(1);
    fprintf(inptr,"f{n}");
    print_function_type(function_type);
    fprintf(inptr,"=");
    generate_signed_integer();
    fprintf(inptr,"*");
    fprintf(inptr,"f{n-1}(");
    generate_factor(2);
    if (function_type == 3 || function_type == 4) {
        fprintf(inptr,",");
        generate_factor(2);
    }
    fprintf(inptr,")");
    fprintf(inptr,"+");
    generate_signed_integer();
    fprintf(inptr,"*");
    fprintf(inptr,"f{n-2}(");
    generate_factor(2);
    if (function_type == 3 || function_type == 4) {
        fprintf(inptr,",");
        generate_factor(2);
    }
    fprintf(inptr,")");
    if(rand_boolean(80)) {
        fprintf(inptr,"+");
        generate_expr(1);
    }
    fprintf(inptr,"\n");
}
void set_infilename(int num){
    infilename[5]=num/1000+'0';
    infilename[6]=num/100%10+'0';
    infilename[7]=num/10%10+'0';
    infilename[8]=num%10+'0';
}
void set_parameter(){
    printf("Please input the number of testcases you want to generate:\n");
    scanf("%d",&output_T);
    /*printf("Please input the maximum value of the depth:\n",MAX_DEPTH);
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
        printf("Please input the percentage of triFunction:\n");
        scanf("%d",&triFunction_percentage);
        printf("Please input the percentage of expr_pow:\n");
        scanf("%d",&expr_pow_percentage);
    }*/
}
void generate_expr(int depth) {
    int record = expected_expr_lenth;
    expected_expr_lenth/=depth;
    int rand_num=randbetween(1,2*expected_expr_lenth);
    if(rand_num==0) rand_num=1;
    for(int i=1;i<=rand_num;++i){
        if(i==1){
            if(rand_boolean(30))
                generate_sign();
        }
        else
            generate_sign();
        generate_term(depth);
    }
    expected_expr_lenth = record;
}
void generate_term(int depth){
    int record = expected_term_lenth;
    expected_term_lenth/=depth;
    int term_lenth=randbetween(1,2*expected_term_lenth);
    if(term_lenth==0) term_lenth=1;
    if(rand_boolean(10))    generate_sign();
    for(int i=1;i<=term_lenth;++i){
        if(i!=1)    fprintf(inptr,"*");
        generate_factor(depth);
    }
    expected_term_lenth=record;
}
void generate_factor(int depth){
    int rand_num=randbetween(1,100);
    if (rand_num<=expression_percentage+triFunction_percentage+function_percentage+derivation_percentage){
        if(depth<=MAX_DEPTH){
            if(rand_num<=derivation_percentage){
                if(!enable_derivation) {
                    generate_factor(depth);
                    return;
                }
                else
                    generate_derivation(depth);
                return;
            }
            else if(rand_num<=triFunction_percentage+derivation_percentage){
                generate_triFunction(depth);
                return;
            }
            else if(rand_num<=triFunction_percentage+function_percentage+derivation_percentage){
                if(enable_function_f || enable_function_g || enable_function_h)
                    generate_function(depth);
                else{
                    generate_triFunction(depth);
                }
                return;
            }
            else{
                fprintf(inptr,"(");
                generate_expr(depth+1);
                fprintf(inptr,")");
                if(rand_boolean(expr_pow_percentage)){
                    fprintf(inptr,"^");
                    generate_normal_integer(3);
                }
            }
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
    else if(rand_num<=expression_percentage+triFunction_percentage+signed_integer_percentage)    
        generate_signed_integer();
    else    generate_pow();
}
void generate_signed_integer(){
    if(rand_boolean(10))    fprintf(inptr,"+");
    else if(rand_boolean(50)) fprintf(inptr,"-");
    generate_normal_integer(MAXN);
}
void generate_normal_integer(int maxval){
    if(rand_boolean(5))
        fprintf(inptr,"0");
    fprintf(inptr,"%d",randbetween(0,maxval));
}
void generate_pow(){
    if((function_type == 3 || function_type == 4) && enable_multi_variables) {
        if(rand_boolean(50))    fprintf(inptr,"x");
        else    fprintf(inptr,"y");
    }
    else {
        if(function_type == 2 && enable_multi_variables) fprintf(inptr,"y");
        else fprintf(inptr,"x");
    }
    if(rand_boolean(80)){
        fprintf(inptr,"^");
        generate_normal_integer(pow_max);
    }
}
void generate_sign(){
    if(rand_boolean(positive_sign_percentage))    fprintf(inptr,"+");
    else    fprintf(inptr,"-");
}
void generate_triFunction(int depth){
    if(rand_boolean(50))    fprintf(inptr,"sin");
    else    fprintf(inptr,"cos");
    fprintf(inptr,"(");
    generate_factor(depth+1);
    fprintf(inptr,")");
    if(rand_boolean(expr_pow_percentage)){
        fprintf(inptr,"^");
        generate_normal_integer(pow_max);
    }
}
void generate_function(int depth){
    if(enable_function_g && enable_function_h && enable_function_f) {
        if(rand_boolean(66)) {
            if(rand_boolean(50)) {
                generate_functionf(depth);
            }
            else {
                generate_functiong(depth);
            }
        }
        else {
            generate_functionf(depth);
        }
    }
    else if(enable_function_g && enable_function_f) {
        if (rand_boolean(50)){
            generate_functionf(depth);
        }
        else {
            generate_functiong(depth);
        }
    }
    else if(enable_function_h && enable_function_f) {
        if (rand_boolean(50)){
            generate_functionf(depth);
        }
        else {
            generate_functionh(depth);
        }
    }
    else if (enable_function_g && enable_function_h) {
        if (rand_boolean(50)){
            generate_functiong(depth);
        }
        else {
            generate_functionh(depth);
        }
    }
    else if (enable_function_f) {
        generate_functionf(depth);
    }
    else if (enable_function_g) {
        generate_functiong(depth);
    }
    else if (enable_function_h) {
        generate_functionh(depth);
    }
}
void generate_functionf(int depth) {
    fprintf(inptr,"f");
    fprintf(inptr,"{%d}",randbetween(0,2));
    fprintf(inptr,"(");
    generate_factor(depth+1);
    if (function_type == 3 || function_type == 4) {
        fprintf(inptr,",");
        generate_factor(depth+1);
    }
    fprintf(inptr,")");
}
void generate_functiong(int depth) {
    fprintf(inptr,"g");
    fprintf(inptr,"(");
    generate_factor(depth+1);
    if (g_function_type == 3 || g_function_type == 4) {
        fprintf(inptr,",");
        generate_factor(depth+1);
    }
    fprintf(inptr,")");
}
void generate_functionh(int depth) {
    fprintf(inptr,"h");
    fprintf(inptr,"(");
    generate_factor(depth+1);
    if (h_function_type == 3 || h_function_type == 4) {
        fprintf(inptr,",");
        generate_factor(depth+1);
    }
    fprintf(inptr,")");
}